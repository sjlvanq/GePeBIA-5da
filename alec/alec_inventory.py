"""
Database of GePeBIA library inventory.
In production, this would be in a real database (PostgreSQL, MongoDB, etc.)
"""

# Library inventory
GEPEBIA_INVENTORY = {
    "adan_buenosayres": {
        "title": "Adán Buenosayres",
        "author": "Leopoldo Marechal",
        "tags": ["NOVEL_EXTENDED", "Experimental", "Argentine Classic"],
        "location": "National Literature Section - Shelf M",
        "copies": [
            {"id": "AB-001", "condition": "Excellent", "status": "Available"},
            {"id": "AB-002", "condition": "Fair (Highlighted)", "status": "Borrowed"},
        ]
    },
    "operation_massacre": {
        "title": "Operation Massacre",
        "author": "Rodolfo Walsh",
        "tags": ["NON_FICTION", "Journalism", "Chronicle"],
        "location": "Journalism and Chronicle Section",
        "copies": [
            {"id": "OM-101", "condition": "Good", "status": "Available"},
            {"id": "OM-102", "condition": "Poor (Loose pages)", "status": "Repair"},
            {"id": "OM-103", "condition": "Excellent", "status": "Available"}
        ]
    },
    "campos_de_castilla": {
        "title": "Fields of Castile",
        "author": "Antonio Machado",
        "tags": ["Poetry", "Generation of 98", "Classic"],
        "location": "Spanish Poetry Section - Shelf M",
        "copies": [
            {"id": "CC-001", "condition": "Excellent", "status": "Available"},
            {"id": "CC-002", "condition": "Fair", "status": "Available"}
        ]
    },
    
    "no_habra_penas_olvido": {
        "title": "No More Sorrows or Forgetting",
        "author": "Osvaldo Soriano",
        "tags": ["Novel", "Dark Humor", "STANDARD"],
        "location": "Latin American Literature Section",
        "copies": [
            {"id": "NP-050", "condition": "Good", "status": "Available"}
        ]
    },
    "el_eternauta": {
        "title": "The Eternaut",
        "author": "Héctor G. Oesterheld & Solano López",
        "tags": ["Comic", "Science Fiction", "Classic", "STANDARD"],
        "location": "Graphic Novel Section - Shelf E",
        "copies": [
            {"id": "ET-001", "condition": "Excellent (Integral Edition)", "status": "Available"},
            {"id": "ET-002", "condition": "Good (Worn softcover)", "status": "Borrowed"},
            {"id": "ET-003", "condition": "Poor (Missing final pages)", "status": "Withdrawn"}
        ]
    },
    "el_eternauta_ii": {
        "title": "The Eternaut II",
        "author": "Héctor G. Oesterheld & Solano López",
        "tags": ["Comic", "Politics", "Drama", "NOVEL_EXTENDED"],
        "location": "Graphic Novel Section - Shelf E",
        "copies": [
            {"id": "ET2-001", "condition": "Excellent", "status": "Available"},
            {"id": "ET2-002", "condition": "Fair (Damaged spine)", "status": "Available"}
        ]
    },
    "cien_anos_soledad": {
        "title": "One Hundred Years of Solitude",
        "author": "Gabriel García Márquez",
        "tags": ["NOVEL_EXTENDED", "Magical Realism", "Classic"],
        "location": "Latin American Literature Section - Shelf G",
        "copies": [
            {"id": "CS-001", "condition": "Excellent", "status": "Borrowed"},
            {"id": "CS-002", "condition": "Good", "status": "Available"}
        ]
    },
    "el_tunel": {
        "title": "The Tunnel",
        "author": "Ernesto Sabato",
        "tags": ["Psychological Novel", "STANDARD"],
        "location": "Argentine Literature Section - Shelf S",
        "copies": [
            {"id": "TN-001", "condition": "Excellent", "status": "Available"}
        ]
    },
    "niebla": {
        "title": "Fog",
        "author": "Miguel de Unamuno",
        "tags": ["Novel", "Nivola", "Generation of 98", "Classic"],
        "location": "Spanish Literature Section - Shelf U",
        "copies": [
            {"id": "NM-001", "condition": "Excellent", "status": "Available"}
        ]
    },
    "el_arbol_ciencia": {
        "title": "The Tree of Knowledge",
        "author": "Pío Baroja",
        "tags": ["Novel", "Generation of 98", "Classic"],
        "location": "Spanish Literature Section - Shelf B",
        "copies": [
            {"id": "AC-001", "condition": "Good", "status": "Available"}
        ]
    },
    "el_hombre_que_fue_jueves": {
        "title": "The Man Who Was Thursday",
        "author": "G. K. Chesterton",
        "tags": ["Novel", "Fiction", "Mystery"],
        "location": "Universal Literature Section - Shelf C",
        "copies": [
            {"id": "HJ-001", "condition": "Excellent", "status": "Borrowed"}
        ]
    },
    "martin_fierro": {
        "title": "The Gaucho Martín Fierro and The Return of Martín Fierro",
        "author": "José Hernández",
        "tags": ["Poetry", "Epic", "Argentine Classic", "REFERENCE"],
        "location": "National Literature Section - Shelf H",
        "copies": [
            {"id": "MF-001", "condition": "Excellent (Bilingual Edition)", "status": "Available"}
        ]
    },
    "los_demonios": {
        "title": "Demons",
        "author": "Fyodor Dostoevsky",
        "tags": ["NOVEL_EXTENDED", "Russian Classic", "Philosophy"],
        "location": "Universal Literature Section - Shelf D",
        "copies": [
            {"id": "LD-001", "condition": "Excellent", "status": "Available"},
            {"id": "LD-002", "condition": "Fair", "status": "Borrowed"}
        ]
    },
    "cristo_vuelve": {
        "title": "Christ Returns",
        "author": "Leonardo Castellani",
        "tags": ["Stories", "Religion", "Philosophy"],
        "location": "National Thought Section - Shelf C",
        "copies": [
            {"id": "CV-001", "condition": "Good", "status": "Available"}
        ]
    },
    "el_mal_de_siglo": {
        "title": "The Sickness of the Century",
        "author": "Manuel Gálvez",
        "tags": ["Essay", "Nationalism", "Politics"],
        "location": "Argentine Essay Section - Shelf G",
        "copies": [
            {"id": "MS-001", "condition": "Excellent", "status": "Available"}
        ]
    },
    "hombre_busca_sentido": {
        "title": "Man's Search for Meaning",
        "author": "Viktor Frankl",
        "tags": ["Non-Fiction", "Psychology", "Logotherapy"],
        "location": "Philosophy and Psychology Section - Shelf F",
        "copies": [
            {"id": "HS-001", "condition": "Excellent", "status": "Available"},
            {"id": "HS-002", "condition": "Good", "status": "Available"}
        ]
    }
}

def get_all_books() -> dict:
    """Returns the complete inventory."""
    return GEPEBIA_INVENTORY


def get_book_by_key(key: str) -> dict:
    """Returns a specific book by its key."""
    return GEPEBIA_INVENTORY.get(key)


def get_all_titles() -> list:
    """Returns list of all titles."""
    return [data["title"] for data in GEPEBIA_INVENTORY.values()]


def get_all_authors() -> list:
    """Returns list of all unique authors."""
    authors = set()
    for data in GEPEBIA_INVENTORY.values():
        authors.add(data.get("author", ""))
    return list(authors)
