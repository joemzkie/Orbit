from dbconn import get_db_connection

def fetch_all_posts():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute("SELECT * FROM posts").fetchall()
        
def fetch_post_by_id(post_id):
      with get_db_connection() as conn:
          with conn.cursor() as cur:
              cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
              return cur.fetchone()

def create_post(data: dict):
      with get_db_connection() as conn:
          with conn.cursor() as cur:
              cur.execute(
                  """
                  INSERT INTO posts (title, content)
                  VALUES (%s, %s)
                  RETURNING *
                  """,
                  (data["title"], data["content"]),
              )
              post = cur.fetchone()
              conn.commit()
              return post
