import socket
import struct
import asyncio
import httpx
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any

logger = logging.getLogger("AreyNetworkScanner")

class NetworkScanner:
    """
    Escáner de red local para descubrir Smart TVs, Chromecast, Roku, Alexa,
    bocinas inteligentes y dispositivos IoT en la red WiFi.
    """

    @staticmethod
    def scan_ssdp(timeout: float = 3.0) -> List[Dict[str, Any]]:
        """
        Escanea dispositivos UPnP/SSDP (Roku, Smart TVs LG/Samsung/Sony, Philips Hue, bocinas).
        """
        devices = []
        ssdp_request = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 2\r\n"
            "ST: ssdp:all\r\n"
            "\r\n"
        )

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        try:
            sock.sendto(ssdp_request.encode(), ("239.255.255.250", 1900))
            discovered_locations = set()

            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    response_text = data.decode(errors="ignore")
                    location = None
                    server = None
                    st = None

                    for line in response_text.splitlines():
                        if line.lower().startswith("location:"):
                            location = line.split(":", 1)[1].strip()
                        elif line.lower().startswith("server:"):
                            server = line.split(":", 1)[1].strip()
                        elif line.lower().startswith("st:"):
                            st = line.split(":", 1)[1].strip()

                    if location and location not in discovered_locations:
                        discovered_locations.add(location)
                        devices.append({
                            "ip": addr[0],
                            "location": location,
                            "server": server,
                            "st": st
                        })
                except socket.timeout:
                    break
        except Exception as e:
            logger.error(f"Error en escaneo SSDP: {e}")
        finally:
            sock.close()

        return devices

    @staticmethod
    async def get_device_details(device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene el nombre amigable y tipo de dispositivo a partir de su descriptor XML.
        """
        location = device_info.get("location")
        ip = device_info.get("ip")
        
        # Reconocimiento especial de Roku
        if location and ":8060" in location:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"http://{ip}:8060/query/device-info")
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        friendly_name = root.findtext("user-device-name") or root.findtext("friendly-device-name") or "Roku TV"
                        model = root.findtext("model-name") or "Roku"
                        return {
                            "name": friendly_name,
                            "type": "Smart TV (Roku)",
                            "ip": ip,
                            "protocol": "roku_ecp",
                            "model": model,
                            "controllable": True
                        }
            except Exception:
                pass

        # UPnP estándar
        if location:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(location)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        ns = {"ns": "urn:schemas-upnp-org:device-1-0"}
                        device = root.find(".//ns:device", ns) or root.find(".//device")
                        if device is not None:
                            fname = device.findtext("ns:friendlyName", namespaces=ns) or device.findtext("friendlyName") or "Dispositivo Smart"
                            mname = device.findtext("ns:manufacturer", namespaces=ns) or device.findtext("manufacturer") or ""
                            model = device.findtext("ns:modelName", namespaces=ns) or device.findtext("modelName") or ""
                            dtype = device.findtext("ns:deviceType", namespaces=ns) or device.findtext("deviceType") or ""
                            
                            category = "Dispositivo Inteligente"
                            if "tv" in fname.lower() or "tv" in model.lower() or "media" in dtype.lower():
                                category = "Smart TV / Reproductor"
                            elif "speaker" in fname.lower() or "audio" in dtype.lower():
                                category = "Bocina Inteligente"

                            return {
                                "name": fname,
                                "type": category,
                                "ip": ip,
                                "manufacturer": mname,
                                "model": model,
                                "protocol": "upnp",
                                "controllable": True
                            }
            except Exception:
                pass

        return {
            "name": f"Dispositivo en {ip}",
            "type": "Dispositivo de Red",
            "ip": ip,
            "protocol": "generic",
            "controllable": False
        }

    @staticmethod
    async def scan_all() -> List[Dict[str, Any]]:
        """
        Escanea la red y retorna todos los dispositivos inteligentes identificados.
        """
        raw_devices = NetworkScanner.scan_ssdp(timeout=2.5)
        tasks = [NetworkScanner.get_device_details(d) for d in raw_devices]
        results = await asyncio.gather(*tasks)
        
        # Eliminar duplicados por IP
        unique_devices = {}
        for r in results:
            if r["ip"] not in unique_devices:
                unique_devices[r["ip"]] = r

        return list(unique_devices.values())

network_scanner = NetworkScanner()
