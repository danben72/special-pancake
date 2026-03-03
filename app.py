import streamlit as st
import pandas as pd
from pathlib import Path

COLOR_MAP = {
    "אבא": "#E74C3C",     # אדום
    "אמא": "#3498DB",     # כחול
    "אילה": "#9B59B6",    # סגול
    "מעיין": "#E67E22"    # כתום
}

FILE = Path("schedule.csv")
PEOPLE = ["אבא", "אמא", "אילה", "מעיין"]
DAYS = ["א'", "ב'", "ג'", "ד'", "ה'", "ו'", "שבת"]

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