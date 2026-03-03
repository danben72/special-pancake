import streamlit as st
import plotly.express as px
import pandas as pd
from pathlib import Path

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

df = load_data()

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

    day_df["start_dt"] = day_df["התחלה"].apply(to_datetime)
    day_df["end_dt"]   = day_df["סיום"].apply(to_datetime)

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
        insidetextanchor="middle"
    )

    fig.update_layout(
        height=450,
        margin=dict(l=20, r=20, t=10, b=20),
        legend_title_text="מי"
    )

    st.plotly_chart(fig, use_container_width=True)

#endregion

#region weekly calendar
cal = build_calendar_df(df)

st.subheader("🗓️ לוח שבועי ויזואלי")

if cal.empty:
    st.info("אין פעילויות עדיין.")
else:
    fig = px.timeline(
        cal,
        x_start="start_dt",
        x_end="end_dt",
        y="יום",
        color="מי",
        text="פעילות",
        hover_data={"מי": True, "פעילות": True, "start_dt": True, "end_dt": True},
        color_discrete_map=COLOR_MAP
    )

    # להפוך את ציר הימים ל"מלמעלה למטה" בצורה יפה
    fig.update_yaxes(autorange="reversed", title=None)

    # פורמט זמנים בציר X
    fig.update_xaxes(
        tickformat="%H:%M",
        title=None
    )

    # טקסט בתוך הבלוקים
    fig.update_traces(textposition="inside", insidetextanchor="middle")

    fig.update_layout(
        height=550,
        margin=dict(l=20, r=20, t=10, b=20),
        legend_title_text="מי"
    )

    st.plotly_chart(fig, use_container_width=True)
#endregion

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
                "יום": day,
                "התחלה": start.strftime("%H:%M"),
                "סיום": end.strftime("%H:%M"),
                "מי": person,
                "פעילות": activity.strip()
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success("נוסף!")

st.subheader("📋 הפעילויות")
# st.dataframe(df, use_container_width=True)
#styled_df = df.style.map(highlight_person, subset=["מי"])
#st.dataframe(styled_df, use_container_width=True)
def highlight_person_column(col):
    return [
        f"background-color: {COLOR_MAP.get(str(val).strip(), 'white')}; "
        f"color: white; font-weight: 700;"
        for val in col
    ]

styled_df = df.style.apply(highlight_person_column, subset=["מי"])
st.dataframe(styled_df, use_container_width=True)

st.divider()
st.subheader("✏️ עריכה / ❌ מחיקה")

if len(df) == 0:
    st.info("אין עדיין פעילויות. תוסיפו אחת למעלה 🙂")
else:
    idx = st.number_input("מספר שורה לעריכה/מחיקה (Index)", min_value=0, max_value=len(df)-1, step=1)

    colA, colB = st.columns(2)

    with colA:
        st.write("עריכת שורה:")
        e_day = st.selectbox("יום (עריכה)", DAYS, index=DAYS.index(df.loc[idx, "יום"]))
        e_start = st.time_input("התחלה (עריכה)", value=pd.to_datetime(df.loc[idx, "התחלה"]).time())
        e_end = st.time_input("סיום (עריכה)", value=pd.to_datetime(df.loc[idx, "סיום"]).time())
        e_person = st.selectbox("מי (עריכה)", PEOPLE, index=PEOPLE.index(df.loc[idx, "מי"]))
        e_activity = st.text_input("פעילות (עריכה)", value=str(df.loc[idx, "פעילות"]))

        if st.button("שמור עריכה"):
            if e_activity.strip() == "":
                st.error("חסר שם פעילות 🙂")
            elif e_end <= e_start:
                st.error("שעת סיום חייבת להיות אחרי שעת התחלה.")
            else:
                df.loc[idx, "יום"] = e_day
                df.loc[idx, "התחלה"] = e_start.strftime("%H:%M")
                df.loc[idx, "סיום"] = e_end.strftime("%H:%M")
                df.loc[idx, "מי"] = e_person
                df.loc[idx, "פעילות"] = e_activity.strip()
                save_data(df)
                st.success("עודכן!")

    with colB:
        st.write("מחיקה:")
        st.warning(f"אתה עומד למחוק: {df.loc[idx, 'יום']} {df.loc[idx, 'התחלה']}-{df.loc[idx, 'סיום']} | {df.loc[idx, 'מי']} | {df.loc[idx, 'פעילות']}")
        if st.button("מחק שורה"):
            df = df.drop(index=idx).reset_index(drop=True)
            save_data(df)
            st.success("נמחק!")
            
