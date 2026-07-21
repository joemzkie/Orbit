from dbconn import get_db_connection

def fetch_all_posts():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute("SELECT * FROM posts").fetchall()
        
def fetch_post_by_id(post_id):
      with get_db_connection() as conn:
          with conn.cursor() as cur:
              cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
              return cur.fetchall()


def main():
    read = fetch_all_posts()
    print(read)

if __name__ == "__main__":
    main()