import json
import os
import random
import streamlit as st

st.set_page_config(page_title="MCQ Study", page_icon="🧠", layout="centered")

QUESTIONS_FILE = "data/questions.json"
STARRED_FILE = "data/starred_questions.json"

@st.cache_data
def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_starred_ids():
    if not os.path.exists(STARRED_FILE):
        with open(STARRED_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return set()

    with open(STARRED_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return set(data)
        except Exception:
            return set()


def save_starred_ids(starred_ids):
    with open(STARRED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(starred_ids)), f, indent=2)


def filter_questions(all_questions, selected_week):
    if selected_week == "All":
        return all_questions[:]
    week_num = int(selected_week.replace("Week ", ""))
    return [q for q in all_questions if q["week"] == week_num]


def prepare_question_pool(questions, quiz_length, shuffle_questions):
    pool = questions[:]
    if shuffle_questions:
        random.shuffle(pool)

    if quiz_length != "All":
        pool = pool[: int(quiz_length)]

    return pool


def get_question_id(question):
    return f"week{question['week']}::{question['question']}"


def start_session(question_pool, mode):
    st.session_state.question_pool = question_pool
    st.session_state.mode = mode
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.correct_count = 0
    st.session_state.wrong_count = 0
    st.session_state.answered = False
    st.session_state.last_result = None
    st.session_state.selected_answer = None
    st.session_state.review_mode = False
    st.session_state.answer_log = {}


def reset_answer_state():
    st.session_state.answered = False
    st.session_state.last_result = None
    st.session_state.selected_answer = None
    st.session_state.review_mode = False


def get_current_question():
    pool = st.session_state.get("question_pool", [])
    idx = st.session_state.get("current_index", 0)

    if not pool or idx >= len(pool):
        return None
    return pool[idx]


def check_answer(question, user_answer):
    correct = question["answer"]

    if question["type"] == "single":
        return user_answer == correct[0]

    if question["type"] == "multiple":
        return set(user_answer) == set(correct)

    return False


def format_correct_answer(question):
    letters = question["answer"]
    return ", ".join([f"{letter}. {question['options'][letter]}" for letter in letters])


def calculate_accuracy(correct, total):
    if total == 0:
        return 0.0
    return round((correct / total) * 100, 2)


def next_question():
    st.session_state.current_index += 1
    reset_answer_state()


def prev_question():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1
        st.session_state.review_mode = True
        q = get_current_question()
        if q:
            qid = get_question_id(q)
            log = st.session_state.answer_log.get(qid)
            if log:
                st.session_state.answered = True
                st.session_state.selected_answer = log["selected_answer"]
                st.session_state.last_result = log["is_correct"]
            else:
                st.session_state.answered = False
                st.session_state.selected_answer = None
                st.session_state.last_result = None


def toggle_star(question):
    qid = get_question_id(question)
    if qid in st.session_state.starred_ids:
        st.session_state.starred_ids.remove(qid)
    else:
        st.session_state.starred_ids.add(qid)
    save_starred_ids(st.session_state.starred_ids)


def is_starred(question):
    return get_question_id(question) in st.session_state.starred_ids


all_questions = load_questions()

if "question_pool" not in st.session_state:
    st.session_state.question_pool = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.correct_count = 0
    st.session_state.wrong_count = 0
    st.session_state.answered = False
    st.session_state.last_result = None
    st.session_state.selected_answer = None
    st.session_state.wrong_questions = []
    st.session_state.mode = "Quiz Mode"
    st.session_state.review_mode = False
    st.session_state.answer_log = {}
    st.session_state.starred_ids = load_starred_ids()

week_options = ["All"] + [f"Week {i}" for i in sorted({q["week"] for q in all_questions})]

st.title("🧠 Weekly MCQ Study Game")
st.caption("Practice weekly assignments in quiz mode or revise in study mode.")

with st.sidebar:
    st.header("Settings")

    selected_week = st.selectbox("Choose Week", week_options)
    mode = st.radio("Mode", ["Quiz Mode", "Study Mode"])

    filtered_questions = filter_questions(all_questions, selected_week)
    total_available = len(filtered_questions)

    if total_available == 0:
        st.warning("No questions found.")
        st.stop()

    length_options = ["5", "10", "20", "All"]
    quiz_length = st.selectbox("Number of Questions", length_options, index=1)

    shuffle_questions = st.checkbox("Shuffle Questions", value=True)
    wrong_only = st.checkbox("Practice Wrong Questions Only", value=False)
    starred_only = st.checkbox("Practice Starred Questions Only", value=False)

    st.write(f"Available questions: **{total_available}**")
    st.write(f"⭐ Starred questions: **{len(st.session_state.starred_ids)}**")

    start_clicked = st.button("Start / Restart Session", use_container_width=True)

    st.divider()
    st.subheader("View Starred Questions")

    starred_questions = [q for q in all_questions if get_question_id(q) in st.session_state.starred_ids]

    if starred_questions:
        with st.expander("Open Starred Questions", expanded=False):
            for i, q in enumerate(starred_questions, start=1):
                st.markdown(f"**{i}. {q['question']}**")
                st.write("Correct Answer:", format_correct_answer(q))
                st.info(q["explanation"])
                st.divider()
    else:
        st.caption("No starred questions yet.")


if start_clicked:
    base_pool = filter_questions(all_questions, selected_week)

    if wrong_only and st.session_state.get("wrong_questions"):
        wrong_set = {q["question"] for q in st.session_state["wrong_questions"]}
        base_pool = [q for q in base_pool if q["question"] in wrong_set]

    if starred_only:
        base_pool = [q for q in base_pool if get_question_id(q) in st.session_state.starred_ids]

    prepared_pool = prepare_question_pool(base_pool, quiz_length, shuffle_questions)
    start_session(prepared_pool, mode)

    if (wrong_only or starred_only) and not prepared_pool:
        st.warning("No questions available for this selection.")
        st.stop()

    st.rerun()


question_pool = st.session_state.get("question_pool", [])

if not question_pool:
    st.info("Choose settings from the sidebar and click **Start / Restart Session**.")
    st.stop()


current_question = get_current_question()

total_questions = len(question_pool)
current_num = min(st.session_state.current_index + 1, total_questions)
progress = st.session_state.current_index / total_questions if total_questions else 0

# Top metrics row
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Correct", st.session_state.correct_count)
with m2:
    st.metric("Wrong", st.session_state.wrong_count)
with m3:
    accuracy = calculate_accuracy(st.session_state.correct_count, st.session_state.current_index)
    st.metric("Accuracy", f"{accuracy}%")

# Progress below metrics
st.write(f"**Progress:** {current_num}/{total_questions}")
st.progress(progress)

if current_question is None:
    final_accuracy = calculate_accuracy(st.session_state.correct_count, total_questions)

    st.success("Session completed 🎉")
    st.subheader("Final Results")
    st.write(f"**Score:** {st.session_state.score} / {total_questions}")
    st.write(f"**Correct:** {st.session_state.correct_count}")
    st.write(f"**Wrong:** {st.session_state.wrong_count}")
    st.write(f"**Accuracy:** {final_accuracy}%")
    st.write(f"**Starred Questions:** {len(st.session_state.starred_ids)}")

    if st.session_state.wrong_questions:
        with st.expander("Review Wrong Questions"):
            for i, q in enumerate(st.session_state.wrong_questions, start=1):
                st.markdown(f"**{i}. {q['question']}**")
                st.write("Correct Answer:", format_correct_answer(q))
                st.info(q["explanation"])
                st.divider()

    st.stop()

# Prev + Star row above question
nav1, nav2 = st.columns([1, 1])
with nav1:
    if st.button("⬅ Previous", use_container_width=True, disabled=(st.session_state.current_index == 0)):
        prev_question()
        st.rerun()
with nav2:
    star_label = "⭐ Unstar" if is_starred(current_question) else "☆ Star"
    if st.button(star_label, use_container_width=True):
        toggle_star(current_question)
        st.rerun()

st.divider()

review_text = " (Review Only)" if st.session_state.review_mode else ""
st.subheader(f"Question {current_num}{review_text}")
st.write(current_question["question"])

options = current_question["options"]

if st.session_state.mode == "Study Mode":
    for key, value in options.items():
        st.write(f"**{key}.** {value}")

    st.success(f"Correct Answer: {format_correct_answer(current_question)}")
    st.info(current_question["explanation"])

    if st.button("Next ➡", use_container_width=True):
        next_question()
        st.rerun()

else:
    if st.session_state.answered:
        # Read-only answered/review mode
        st.write("**Options:**")
        if current_question["type"] == "single":
            for key, value in options.items():
                marker = " ← Your choice" if st.session_state.selected_answer == key else ""
                st.write(f"**{key}.** {value}{marker}")
        else:
            selected = st.session_state.selected_answer or []
            for key, value in options.items():
                marker = " ← Your choice" if key in selected else ""
                st.write(f"**{key}.** {value}{marker}")

        if st.session_state.last_result:
            st.success("Correct ✅")
        else:
            st.error("Wrong ❌")

        if current_question["type"] == "single":
            st.write(f"**Your Answer:** {st.session_state.selected_answer}")
        else:
            selected = st.session_state.selected_answer or []
            st.write(f"**Your Answer:** {', '.join(selected) if selected else 'No option selected'}")

        st.write(f"**Correct Answer:** {format_correct_answer(current_question)}")
        st.info(f"**Explanation:** {current_question['explanation']}")

        if not st.session_state.review_mode:
            if st.button("Next Question ➡", use_container_width=True):
                next_question()
                st.rerun()
        else:
            st.caption("Review mode: previous answers are locked and cannot be edited.")

    else:
        if current_question["type"] == "single":
            user_answer = st.radio(
                "Choose one answer:",
                options=list(options.keys()),
                format_func=lambda x: f"{x}. {options[x]}",
                key=f"single_{st.session_state.current_index}"
            )
        elif current_question["type"] == "multiple":
            user_answer = st.multiselect(
                "Choose all correct answers:",
                options=list(options.keys()),
                format_func=lambda x: f"{x}. {options[x]}",
                key=f"multiple_{st.session_state.current_index}"
            )
        else:
            st.error("Unknown question type.")
            st.stop()

        if st.button("Submit Answer", use_container_width=True):
            is_correct = check_answer(current_question, user_answer)

            st.session_state.answered = True
            st.session_state.selected_answer = user_answer
            st.session_state.last_result = is_correct
            st.session_state.review_mode = False

            qid = get_question_id(current_question)
            st.session_state.answer_log[qid] = {
                "selected_answer": user_answer,
                "is_correct": is_correct
            }

            if is_correct:
                st.session_state.score += 1
                st.session_state.correct_count += 1
            else:
                st.session_state.wrong_count += 1
                if current_question not in st.session_state.wrong_questions:
                    st.session_state.wrong_questions.append(current_question)

            st.rerun()