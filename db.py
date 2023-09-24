import sqlite3

langlist={"th": "Thai",
          "jp":"Japanese",
          "en": "English"
          }

def check_lang_target(groupid):
    #try:
    conn = sqlite3.connect('babel.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT lang FROM setting where groupid='{groupid}'")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if rows == []:
        return 'en'
    else:
        for row in rows:
            return row[0]
    #except Exception as e :
    #    print(f'check_lang_target e:{e}')
    #    cursor.close()
    #    conn.close()

def update_lang_target(groupid,lang):
    try:
        conn = sqlite3.connect('babel.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT lang FROM setting where groupid='{groupid}'")
        rows = cursor.fetchall()
        if rows == []:
            cursor.execute('INSERT INTO setting (groupid, lang) VALUES (?, ?)', (groupid, lang))
            conn.commit()
        else:
            cursor.execute('UPDATE setting SET lang = ? WHERE groupid = ?', (lang, groupid))
            conn.commit()
        cursor.close()
        conn.close()
    except Exception as e :
        logger.error(f'e:{e}')
        cursor.close()
        conn.close()

def show():
    conn = sqlite3.connect('babel.db')
    cursor = conn.cursor()
    #cursor.execute('''
    #    CREATE TABLE IF NOT EXISTS setting (
    #        id INTEGER PRIMARY KEY,
    #        groupid TEXT,
    #        lang TEXT
    #    )
    #''')

    #cursor.execute('INSERT INTO setting (groupid, lang) VALUES (?, ?)', ('55678', 'th'))
    #conn.commit()
    cursor.execute('SELECT * FROM setting')
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    
    cursor.close()
    conn.close()


#print(check_lang_target("Ua1328e90858bad89e9e14c6f26aef63b"))
print(check_lang_target("C48224f7f7448e35a90a84554c3975f0e"))
#update_lang_target("C48224f7f7448e35a90a84554c3975f0e","jp")
show()
