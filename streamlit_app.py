import os
import streamlit as st
from supabase import create_client, Client

# 1. 初始化 Supabase 雲端資料庫連線 (自動讀取你剛剛在 Vercel 設定的密碼)
url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
key: str = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

# 防止未設定環境變數時報錯，但在 Vercel 線上會正常運作
if not url or not key:
    st.warning("⚠️ 尚未偵測到雲端資料庫連線設定，本機測試前請確保設定正確。")
    supabase: Client = None
else:
    supabase: Client = create_client(url, key)

st.title("🎈 雲端同步系統資料更新")
st.write("不論在哪台電腦更新，所有人都能同步看見改動！")

# 2. 畫面上方：讓使用者輸入資料並新增到雲端
st.subheader("➕ 新增/更新系統資料")
with st.form("add_data_form", clear_on_submit=True):
    user_input = st.text_input("輸入你想更新的內容：", placeholder="例如：今日庫存更新...")
    submit_button = st.form_submit_form_button = st.form_submit_button("確認更新並推上雲端")

    if submit_button and user_input:
        if supabase:
            try:
                # ⚠️ 這裡的 'posts' 是你在 Supabase 建立的資料表名稱，'content' 是欄位名稱
                data, count = supabase.table('posts').insert({"content": user_input}).execute()
                st.success("✅ 資料已成功同步至雲端資料庫！")
            except Exception as e:
                st.error(f"寫入失敗，請確認 Supabase 的資料表名稱是否為 'posts'。錯誤訊息: {e}")
        else:
            st.error("雲端資料庫未連線成功。")

# 3. 畫面下方：從雲端撈取所有歷史資料並顯示
st.subheader("📋 目前雲端最新同步資料")
if supabase:
    try:
        # 從雲端資料庫抓取最新更新的所有內容
        response = supabase.table('posts').select("*").order('id', desc=True).execute()
        records = response.data
        
        if records:
            for item in records:
                # 假設你的資料欄位叫做 'content'
                st.info(f"🔹 {item.get('content', '無內容')}")
        else:
            st.write("惝目前雲端尚無資料，請在上方輸入第一筆更新！")
    except Exception as e:
        st.write("讀取雲端資料失敗，請確認你的 Supabase 是否已建立名為 'posts' 的資料表。")
