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

def fetch_post_latest():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM posts ORDER BY id DESC LIMIT 10;"
            )
            return cur.fetchall()
        
def delete_post(post_id: int):
      with get_db_connection() as conn:
          with conn.cursor() as cur:
              # `(post_id,)` is a one-item tuple; `(post_id)` is only an integer.
              cur.execute("DELETE FROM posts WHERE id = %s RETURNING *", (post_id,))
              post = cur.fetchone()
              conn.commit()
              return post
          
def update_post(post_id: int, data: dict):
      with get_db_connection() as conn:
          with conn.cursor() as cur:
              cur.execute(
                  """
                  UPDATE posts
                  SET title = %s, content = %s, published = %s
                  WHERE id = %s
                  RETURNING *
                  """,
                  (
                      data["title"],
                      data["content"],
                      data["published"],
                      post_id,
                  ),
              )
              updated_post = cur.fetchone()
              conn.commit()
              return updated_post
