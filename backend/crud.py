from dbconn import get_db_connection

def fetch_all_posts():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute("SELECT * FROM posts").fetchall()

def main():
    read = fetch_all_posts()
    print(read)

if __name__ == "__main__":
    main()