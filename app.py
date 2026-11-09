import os
import hashlib
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="雲端同步系統", page_icon="☁️")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY", "")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("請設定 SUPABASE_URL 和 Supabase publishable/anon key。")
    st.stop()

# 每個瀏覽器工作階段各自保存登入狀態，避免不同使用者共用
if "supabase_client" not in st.session_state:
    st.session_state.supabase_client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )

supabase = st.session_state.supabase_client


def auto_save(todo_id: int, widget_key: str) -> None:
    """內容變更時，立即更新目前登入者自己的資料。"""
    try:
        content = st.session_state[widget_key]
        (
            st.session_state.supabase_client
            .table("todos")
            .update({"content": content})
            .eq("id", todo_id)
            .eq("user_id", st.session_state.user_id)
            .execute()
        )
        st.session_state["save_status"] = "已同步到雲端"
        st.session_state.pop("save_error", None)
    except Exception as e:
        st.session_state["save_error"] = str(e)


st.title("☁️ 雲端同步系統")

# 登入或註冊
if "user_id" not in st.session_state:
    mode = st.radio("操作", ["登入", "註冊"], horizontal=True)

    with st.form("auth_form"):
        email = st.text_input("電子郵件")
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button(mode)

    if submitted:
        try:
            if mode == "登入":
                result = supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                st.session_state.user_id = result.user.id
                st.session_state.user_email = email
                st.rerun()
            else:
                result = supabase.auth.sign_up(
                    {"email": email, "password": password}
                )

                if result.session and result.user:
                    st.session_state.user_id = result.user.id
                    st.session_state.user_email = email
                    st.rerun()
                else:
                    st.success("註冊已送出，請先查看電子郵件完成驗證，再登入。")
        except Exception as e:
            st.error(f"{mode}失敗：{e}")

    st.stop()

user_id = st.session_state.user_id
st.caption(f"已登入：{st.session_state.get('user_email', '')}")

if st.button("登出"):
    try:
        supabase.auth.sign_out()
    finally:
        for key in ("user_id", "user_email", "supabase_client"):
            st.session_state.pop(key, None)
        st.rerun()

# 新增資料
st.subheader("➕ 新增資料")

with st.form("add_form", clear_on_submit=True):
    new_content = st.text_input(
        "輸入內容",
        placeholder="例如：今日庫存更新",
    )
    add_clicked = st.form_submit_button("新增資料")

if add_clicked:
    if not new_content.strip():
        st.warning("請先輸入內容。")
    else:
        try:
            supabase.table("todos").insert(
                {
                    "content": new_content.strip(),
                    "user_id": user_id,
                }
            ).execute()
            st.session_state["save_status"] = "已新增並同步到雲端"
            st.rerun()
        except Exception as e:
            st.error(f"新增失敗：{e}")

st.subheader("📋 雲端資料")


@st.fragment(run_every="5s")
def show_todos():
    client = st.session_state.supabase_client
    current_user_id = st.session_state.user_id

    try:
        result = (
            client.table("todos")
            .select("id, content")
            .eq("user_id", current_user_id)
            .order("id", desc=True)
            .execute()
        )

        records = result.data or []

        if not records:
            st.info("目前沒有資料，請先新增一筆。")

        for item in records:
            todo_id = item["id"]
            content = item.get("content") or ""

            # 雲端內容變更時換一個 widget key，讓其他電腦的更新能顯示
            digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
            widget_key = f"todo_{todo_id}_{digest}"

            with st.container(border=True):
                left, right = st.columns([5, 1])

                with left:
                    st.text_area(
                        "內容",
                        value=content,
                        key=widget_key,
                        on_change=auto_save,
                        args=(todo_id, widget_key),
                        label_visibility="collapsed",
                    )

                with right:
                    if st.button("刪除", key=f"delete_{todo_id}"):
                        (
                            client.table("todos")
                            .delete()
                            .eq("id", todo_id)
                            .eq("user_id", current_user_id)
                            .execute()
                        )
                        st.rerun()

        if st.session_state.get("save_status"):
            st.caption(st.session_state["save_status"])

        if st.session_state.get("save_error"):
            st.error(f"自動儲存失敗：{st.session_state['save_error']}")

    except Exception as e:
        st.error(f"讀取資料失敗：{e}")


show_todos()
