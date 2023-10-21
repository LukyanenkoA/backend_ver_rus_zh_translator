import sqlite3

import os

print(os.getcwd())

list_of_dicts = []
with open('resources/dabkrs_v91_1.u8', encoding='utf-16') as file:
    text = file.read()
    lines = text.split('\n\n')
    dict_lines = list(lines)


    # define functions

    def parse_line(line):
        parsed = {}
        if line == '':
            dict_lines.remove(line)
            return 0
        line = line.rstrip('\n\n')
        line = line.split('\n')
        if len(line) <= 1:
            return 0
        russian = ', '.join(line[2:])
        simplified = line[0]
        pinyin = line[1]
        parsed['simplified'] = simplified
        parsed['pinyin'] = pinyin
        parsed['russian'] = russian
        list_of_dicts.append(parsed)


    def main():

        # make each line into a dictionary
        print("Parsing dictionary . . .")
        for line in dict_lines:
            parse_line(line)
        # remove entries for surnames from the data (optional):
        print('Done!')

        return list_of_dicts

parsed_dict = main()

print(parsed_dict)


def create_table():
    f = False
    try:
        sqlite_connection = sqlite3.connect('resources/database.db')
        cursor = sqlite_connection.cursor()
        print("Connected to SQLite")

        sql_create_zh_rus_table = """ CREATE TABLE IF NOT EXISTS words_rus (
                                                id INTEGER NOT NULL UNIQUE PRIMARY KEY,
                                                simplified VARCHAR UNIQUE,
                                                russian VARCHAR,
                                                pinyin VARCHAR
                                            ); """
        cursor.execute(sql_create_zh_rus_table)
        cursor.close()
    except sqlite3.Error as error:
        print("Error while working with SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Connection to SQLite is closed")
            return f


def insert_tuples():
    i = 1
    try:
        sqlite_connection = sqlite3.connect('resources/database.db')
        cursor = sqlite_connection.cursor()
        print("Connected to SQLite")
        for line in parsed_dict:
            f = False
            sql_select_query = """select * from words_rus where simplified = ?"""
            cursor.execute(sql_select_query, (line["simplified"],))
            record = cursor.fetchall()
            if record:
                f = True
            if not f and (line["pinyin"] != '_'):
                sqlite_insert_with_param = """INSERT INTO words_rus
                                      (id, simplified, russian, pinyin)
                                       VALUES(?, ?, ?, ?);"""
                data_tuple = (i, line["simplified"], line["russian"], line["pinyin"])
                cursor.execute(sqlite_insert_with_param, data_tuple)
                i += 1
        sqlite_connection.commit()
        print("success ", cursor.rowcount)
        cursor.close()

    except sqlite3.Error as error:
        print("Error while working with SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Connection to SQLite is closed")


def delete_all():
    try:
        sqlite_connection = sqlite3.connect('resources/database.db')
        cursor = sqlite_connection.cursor()
        print("Connected to SQLite")
        sql_delete_query = """DELETE from words_rus"""
        cursor.execute(sql_delete_query)
        sqlite_connection.commit()
        print("success ", cursor.rowcount)
        cursor.close()

    except sqlite3.Error as error:
        print("Error while working with SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Connection to SQLite is closed")


def delete_tuple():
    try:
        sqlite_connection = sqlite3.connect('resources/database.db')
        cursor = sqlite_connection.cursor()
        print("Connected to SQLite")
        sql_delete_query = """DELETE from words_rus where pinyin = '_'"""
        cursor.execute(sql_delete_query)
        sqlite_connection.commit()
        print("success ", cursor.rowcount)
        cursor.close()

    except sqlite3.Error as error:
        print("Error while working with SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Connection to SQLite is closed")


# create_table()
insert_tuples()
# delete_tuple()
