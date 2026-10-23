package com.edgerunners.scamcheck.ui.spell

import androidx.annotation.StringRes
import com.edgerunners.scamcheck.R

// DEMO-FAKE: sample contacts and "your circle" from the Spellbreaker prototype. The app doesn't
// read the phone's contacts and the backend has no circle yet; numbers are masked on purpose.

data class DemoContact(
    val id: String,
    val name: String,
    val number: String,
    @StringRes val relation: Int? = null,
    val onApp: Boolean = false,
    /** Set when this person is in the user's circle; says how. */
    @StringRes val circle: Int? = null,
)

object DemoPeople {
    const val TRUSTED_ID = "arjun"
    const val PROTECTED_ID = "mum"

    val contacts = listOf(
        DemoContact("aditi", "Aditi Sharma", "+91 98140 2XXXX"),
        DemoContact("arjun", "Arjun", "+91 98722 4XXXX", R.string.sb_rel_brother, onApp = true, circle = R.string.sb_rel_told),
        DemoContact("dad", "Dad", "+91 99150 1XXXX"),
        DemoContact("clinic", "Dr Kaur’s Clinic", "0172 27X XXXX"),
        DemoContact("gurpreet", "Gurpreet Singh", "+91 97800 3XXXX", onApp = true),
        DemoContact("karan", "Karan Malhotra", "+91 98880 6XXXX"),
        DemoContact("mum", "Mum", "+91 98154 7XXXX", onApp = true, circle = R.string.sb_rel_lookout),
        DemoContact("bank", "My bank", "1800 XXX XXXX", R.string.sb_rel_bank),
        DemoContact("neha", "Neha Gupta", "+91 99880 5XXXX"),
        DemoContact("rahul", "Rahul Verma", "+91 98030 8XXXX"),
        DemoContact("simran", "Simran Kaur", "+91 97790 9XXXX", onApp = true),
    )

    fun byId(id: String?): DemoContact? = contacts.firstOrNull { it.id == id }

    val trusted: DemoContact get() = byId(TRUSTED_ID)!!
    val protectedPerson: DemoContact get() = byId(PROTECTED_ID)!!

    /** Contacts whose name or number matches [query], grouped by first letter. */
    fun search(query: String): List<Pair<Char, List<DemoContact>>> {
        val q = query.trim().lowercase()
        val digits = q.filter { it.isDigit() }
        return contacts
            .filter { c ->
                q.isEmpty() || c.name.lowercase().contains(q) ||
                    (digits.isNotEmpty() && c.number.filter { it.isDigit() }.contains(digits))
            }
            .groupBy { it.name.first().uppercaseChar() }
            .toList()
    }

    fun matchNumber(dial: String): DemoContact? =
        if (dial.isEmpty()) null else contacts.firstOrNull { it.number.filter { ch -> ch.isDigit() }.contains(dial) }
}
