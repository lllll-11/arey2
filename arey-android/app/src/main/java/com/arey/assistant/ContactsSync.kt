package com.arey.assistant

import android.content.Context
import android.provider.ContactsContract
import android.util.Log

class ContactsSync(private val context: Context) {

    private val tag = "ContactsSync"

    /**
     * Lee la lista de contactos con número de teléfono del dispositivo.
     */
    fun readContacts(): List<Map<String, String>> {
        val contactsList = mutableListOf<Map<String, String>>()
        val uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER
        )

        try {
            val cursor = context.contentResolver.query(uri, projection, null, null, null)
            cursor?.use {
                val nameIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)

                while (it.moveToNext()) {
                    val name = if (nameIndex != -1) it.getString(nameIndex) else ""
                    val number = if (numberIndex != -1) it.getString(numberIndex) else ""

                    if (name.isNotBlank() && number.isNotBlank()) {
                        contactsList.add(
                            mapOf(
                                "name" to name.trim(),
                                "phone" to number.trim().replace(" ", "").replace("-", "")
                            )
                        )
                    }
                }
            }
            Log.d(tag, "Total contactos leídos: ${contactsList.size}")
        } catch (e: Exception) {
            Log.e(tag, "Error leyendo contactos: ${e.message}")
        }

        return contactsList
    }
}
