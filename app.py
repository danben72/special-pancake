import streamlit as st
import plotly.express as px
import pandas as pd
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid


SHEET_ID = st.secrets["GSHEET_ID"]
TAB_NAME = "schedule"

DAY_TO_NUM = {"א'": 0, "ב'": 1, "ג'": 2, "ד'": 3, "ה'": 4, "ו'": 5, "שבת": 6}

COLOR_MAP = {
    "אבא": "#E74C3C",     # אדום
    "אמא": "#3498DB",     # כחול
    "אילה": "#9B59B6",    # סגול
    "מעיין": "#E67E22"    # כתום
}

FILE = Path("schedule.csv")
PEOPLE = ["אבא", "אמא", "אילה", "מעיין"]
DAYS = ["א'", "ב'", "ג'", "ד'", "ה'", "ו'", "שבת"]


def gs_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(creds)

def load_data_gsheet() -> pd.DataFrame:
    gc = gs_client()
    ws = gc.open_by_key(SHEET_ID).worksheet(TAB_NAME)
    rows = ws.get_all_records()  # list of dicts
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["id","יום","התחלה","סיום","מי","פעילות"])
    return df

def append_row_gsheet(row: dict):
    gc = gs_client()
    ws = gc.open_by_key(SHEET_ID).worksheet(TAB_NAME)
    ws.append_row([row["id"], row["יום"], row["התחלה"], row["סיום"], row["מי"], row["פעילות"]])

def update_row_gsheet(row_id: str, new_row: dict):
    gc = gs_client()
    ws = gc.open_by_key(SHEET_ID).worksheet(TAB_NAME)
    data = ws.get_all_values()
    # data[0] headers
    for i in range(1, len(data)):
        print(f"Checking row {i}: {data[i][0]} against {row_id}")
        if data[i][0] == row_id:
            # row index in gspread is 1-based
            print(f"Found row to update at index {i}")
            sheet_row = i + 1
            ws.update(f"A{sheet_row}:F{sheet_row}", [[
                new_row["id"], new_row["יום"], new_row["התחלה"], new_row["סיום"], new_row["מי"], new_row["פעילות"]
            ]])
            return
    raise ValueError("Row id not found")

def delete_row_gsheet(row_id: str):
    gc = gs_client()
    ws = gc.open_by_key(SHEET_ID).worksheet(TAB_NAME)
    data = ws.get_all_values()
    for i in range(1, len(data)):
        if data[i][0] == row_id:
            ws.delete_rows(i + 1)
            return
    raise ValueError("Row id not found")

def new_id():
    return uuid.uuid4().hex[:10]

def to_datetime_for_week(day_str, hhmm, base_date="2026-01-05"):
    """
    base_date = יום שני כלשהו. זה רק כדי לבנות תאריכים "פיקטיביים" לאותו שבוע.
    2026-01-05 הוא יום שני.
    """
    base = pd.Timestamp(base_date)  # Monday
    day_offset = DAY_TO_NUM.get(day_str, 0)
    h, m = map(int, str(hhmm).split(":"))
    return base + pd.Timedelta(days=day_offset) + pd.Timedelta(hours=h, minutes=m)

def build_calendar_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    cal = df.copy()
    # ניקוי קטן
    cal["מי"] = cal["מי"].astype(str).str.strip()
    cal["יום"] = cal["יום"].astype(str).str.strip()

    cal["start_dt"] = cal.apply(lambda r: to_datetime_for_week(r["יום"], r["התחלה"]), axis=1)
    cal["end_dt"]   = cal.apply(lambda r: to_datetime_for_week(r["יום"], r["סיום"]), axis=1)

    # תווית יפה לבלוק
    cal["label"] = cal["פעילות"].astype(str) + " — " + cal["מי"].astype(str)

    # סדר ימים יפה (כדי שה-Y יהיה א'..שבת)
    cal["day_num"] = cal["יום"].map(DAY_TO_NUM).fillna(0).astype(int)
    cal = cal.sort_values(["day_num", "start_dt"]).drop(columns=["day_num"])

    return cal



def highlight_person(val):
    color = COLOR_MAP.get(val, "white")
    return f"background-color: {color}; font-weight: 700;"

def load_data():
    if FILE.exists():
        df = pd.read_csv(FILE)
        # keep types friendly
        return df
    return pd.DataFrame(columns=["יום", "התחלה", "סיום", "מי", "פעילות"])

def save_data(df: pd.DataFrame):
    df.to_csv(FILE, index=False)

st.set_page_config(page_title="לוז משפחתי", layout="wide")
st.title("📅 לוז משפחתי שבועי")

# # call new_id 40 times and print its results to check for uniqueness
# for _ in range(40):
#      print(new_id())


#df = load_data()
df = load_data_gsheet()
# # Force stable dtypes (prevents Arrow serialization issues)
# for c in ["id", "יום", "התחלה", "סיום", "מי", "פעילות"]:
#     if c in df.columns:
#         df[c] = df[c].astype("string").fillna("").str.strip()

#region daily view 
st.subheader("📅 תצוגה יומית")

selected_day = st.selectbox("בחר יום", DAYS)

# סינון לפי יום
day_df = df[df["יום"].str.strip() == selected_day].copy()

if day_df.empty:
    st.info("אין פעילויות ביום הזה.")
else:
    base_date = pd.Timestamp("2026-01-01")

    def to_datetime(hhmm):
        h, m = map(int, str(hhmm).split(":"))
        return base_date + pd.Timedelta(hours=h, minutes=m)

    # המרת עמודות התחלה וסיום לזמנים אמיתיים כדי ש-Plotly יוכל להציג אותם נכון
    day_df["start_dt"] = day_df["התחלה"].apply(to_datetime)
    day_df["end_dt"]   = day_df["סיום"].apply(to_datetime)

    # תווית יפה לבלוק 
    fig = px.timeline(
        day_df,
        x_start="start_dt",
        x_end="end_dt",
        y="מי",
        color="מי",
        text="פעילות",
        color_discrete_map=COLOR_MAP
    )

    fig.update_yaxes(title=None)
    fig.update_xaxes(
        tickformat="%H:%M",
        title=None
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        # add outline to blocks for better visibility
        marker_line_color="black",
        marker_line_width=0.5
    )

    row_height = 60  # כמה פיקסלים לכל בן משפחה
    fig.update_layout(
        height=row_height * len(day_df["מי"].unique()),
        margin=dict(l=20, r=20, t=10, b=20),
        legend_title_text="מי"
    )

    fig.update_xaxes(range=[
    base_date + pd.Timedelta(hours=6),
    base_date + pd.Timedelta(hours=23)])

    fig.update_xaxes(showgrid=True, dtick=3600000)

    st.plotly_chart(fig, use_container_width=True)

#endregion

# #region weekly calendar
# cal = build_calendar_df(df)

# st.subheader("🗓️ לוח שבועי ויזואלי")

# if cal.empty:
#     st.info("אין פעילויות עדיין.")
# else:
#     fig = px.timeline(
#         cal,
#         x_start="start_dt",
#         x_end="end_dt",
#         y="יום",
#         color="מי",
#         text="פעילות",
#         hover_data={"מי": True, "פעילות": True, "start_dt": True, "end_dt": True},
#         color_discrete_map=COLOR_MAP
#     )

#     # להפוך את ציר הימים ל"מלמעלה למטה" בצורה יפה
#     fig.update_yaxes(autorange="reversed", title=None)

#     # פורמט זמנים בציר X
#     fig.update_xaxes(
#         tickformat="%H:%M",
#         title=None
#     )

#     # טקסט בתוך הבלוקים
#     fig.update_traces(textposition="inside", insidetextanchor="middle")

#     fig.update_layout(
#         height=550,
#         margin=dict(l=20, r=20, t=10, b=20),
#         legend_title_text="מי"
#     )

#     st.plotly_chart(fig, use_container_width=True)
# #endregion

with st.expander("➕ הוספת פעילות", expanded=True):
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 3])
    day = c1.selectbox("יום", DAYS)
    start = c2.time_input("התחלה")
    end = c3.time_input("סיום")
    person = c4.selectbox("מי", PEOPLE)
    activity = c5.text_input("פעילות")

    if st.button("הוסף"):
        if activity.strip() == "":
            st.error("חסר שם פעילות 🙂")
        elif end <= start:
            st.error("שעת סיום חייבת להיות אחרי שעת התחלה.")
        else:
            new_row = {
                "id": new_id(),
                "יום": day,
                "התחלה": start.strftime("%H:%M"),
                "סיום": end.strftime("%H:%M"),
                "מי": person,
                "פעילות": activity.strip()
            }
            append_row_gsheet(new_row)            
            st.success("נוסף!")

st.subheader("📋 הפעילויות")
def highlight_person_column(col):
    return [
        f"background-color: {COLOR_MAP.get(str(val).strip(), 'white')}; "
        f"color: white; font-weight: 700;"
        for val in col
    ]

# Apply the styling function to the "מי" column and get a styled DataFrame
styled_df = df.drop(columns=["id"]).style.apply(highlight_person_column, subset=["מי"])
# Display the styled DataFrame in Streamlit with container width and without the index
st.dataframe(styled_df, use_container_width=True, hide_index=True)

#########################
# Edit / Delete section #
#########################

st.divider()
st.subheader("✏️ עריכה / ❌ מחיקה")

if len(df) == 0:
    st.info("אין עדיין פעילויות. תוסיפו אחת למעלה 🙂")
else:
    # selected_id = st.selectbox("בחר פעילות לעריכה", df["id"].tolist())    
    # Create display labels combining multiple fields
    df["display_label"] = (
        df["מי"] + " | " + 
        df["יום"] + " " + 
        df["התחלה"] +
         "-" + df["סיום"] + " | " + 
        df["פעילות"]
    )
    
    selected_label = st.selectbox("בחר פעילות לעריכה", df["display_label"].tolist())
    selected_id = df[df["display_label"] == selected_label]["id"].iloc[0]
    # find index of selected_id
    selected_idx = df[df["id"] == selected_id].index[0] if selected_id in df["id"].values else None
    if selected_id in df["id"].values:
        row = df[df["id"] == selected_id].iloc[0]
    else:
        st.error("הזדהות לא נמצאה. אנא בחר מזהה תקין.")
        st.stop()

    colA, colB = st.columns(2)

    with colA:
        st.write("עריכת שורה:")
        e_day = st.selectbox("יום (עריכה)", DAYS, index=DAYS.index(df.loc[selected_idx, "יום"]))
        e_start = st.time_input("התחלה (עריכה)", value=pd.to_datetime(df.loc[selected_idx, "התחלה"]).time())
        e_end = st.time_input("סיום (עריכה)", value=pd.to_datetime(df.loc[selected_idx, "סיום"]).time())
        e_person = st.selectbox("מי (עריכה)", PEOPLE, index=PEOPLE.index(df.loc[selected_idx, "מי"]))
        e_activity = st.text_input("פעילות (עריכה)", value=str(df.loc[selected_idx, "פעילות"]))

        if st.button("שמור עריכה"):
            if e_activity.strip() == "":
                st.error("חסר שם פעילות 🙂")
            elif e_end <= e_start:
                st.error("שעת סיום חייבת להיות אחרי שעת התחלה.")
            else:
                edited_row = {
                 "id": selected_id,
                 "יום": e_day,
                 "התחלה": e_start.strftime("%H:%M"),
                 "סיום": e_end.strftime("%H:%M"),
                 "מי": e_person.strip(),
                 "פעילות": e_activity.strip()
                }
                update_row_gsheet(selected_id, edited_row)
                #df = load_data_gsheet()
                st.success("עודכן!")
                st.rerun()


    with colB:
        st.write("מחיקה:")
        st.warning(f"אתה עומד למחוק: {df.loc[selected_idx, 'מי']} | {df.loc[selected_idx, 'יום']} {df.loc[selected_idx, 'התחלה']}-{df.loc[selected_idx, 'סיום']} | {df.loc[selected_idx, 'פעילות']}")
        if st.button("מחק שורה"):
            delete_row_gsheet(selected_id)
            st.success("נמחק!") 
            st.rerun()
            # df = load_data_gsheet()


