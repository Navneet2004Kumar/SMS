from flask import Flask, render_template, request, redirect
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

app = Flask(__name__)

# ── DB helper ────────────────────────────────────────────────────────────────

def get_db():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "student_db")
    )
    return conn


# ── Validation helpers ─────────────────────────────────────────────────────

def validate_student_data(cursor, name, dob, gender, contact, course_id, student_id=None):
    """
    Returns an error message string if validation fails, otherwise None.
    student_id is passed during update so the current record is excluded
    from the 'contact must be unique' check.
    """
    name = (name or "").strip()
    contact = (contact or "").strip()

    # Name: only alphabets and spaces
    if not name:
        return "Name cannot be empty."
    if not name.replace(" ", "").isalpha():
        return "Name should contain only alphabets."

    # Contact: exactly 10 digits
    if not contact.isdigit() or len(contact) != 10:
        return "Contact number must be exactly 10 digits."

    # Contact: must be unique
    if student_id:
        cursor.execute(
            "SELECT student_id FROM students WHERE contact=%s AND student_id != %s",
            (contact, student_id)
        )
    else:
        cursor.execute("SELECT student_id FROM students WHERE contact=%s", (contact,))
    if cursor.fetchone():
        return "This contact number is already registered with another student."

    # DOB: required and not in the future
    if not dob:
        return "Date of birth is required."
    try:
        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format."
    if dob_date > datetime.today().date():
        return "Date of birth cannot be in the future."

    # Gender: required
    if not gender:
        return "Gender is required."

    # Course: must be selected and must exist
    if not course_id:
        return "Please select a course."
    cursor.execute("SELECT course_id FROM courses WHERE course_id=%s", (course_id,))
    if not cursor.fetchone():
        return "Selected course does not exist."

    return None


# ── Home ─────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.student_id, s.name, s.dob, s.gender, s.contact, c.course_name, s.course_id
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.course_id
    """)
    students = cursor.fetchall()

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("index.html", students=students, courses=courses)


# ── Add Student ───────────────────────────────────────────────────────────────

@app.route("/add", methods=["POST"])
def add_student():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    name = request.form["name"]
    dob = request.form["dob"]
    gender = request.form["gender"]
    contact = request.form["contact"]
    course_id = request.form["course_id"]

    error = validate_student_data(cursor, name, dob, gender, contact, course_id)
    if error:
        cursor.close()
        conn.close()
        return error

    cursor.execute(
        "INSERT INTO students (name, dob, gender, contact, course_id) VALUES (%s,%s,%s,%s,%s)",
        (name.strip(), dob, gender, contact.strip(), course_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")


# ── Edit ──────────────────────────────────────────────────────────────────────

@app.route("/edit/<int:student_id>")
def edit(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    student = cursor.fetchone()

    # Fix: format date so the HTML date input renders correctly
    if student and student["dob"]:
        student["dob"] = student["dob"].strftime("%Y-%m-%d")

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("edit.html", student=student, courses=courses)


# ── Update ────────────────────────────────────────────────────────────────────

@app.route("/update/<int:student_id>", methods=["POST"])
def update(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    name = request.form["name"]
    dob = request.form["dob"]
    gender = request.form["gender"]
    contact = request.form["contact"]
    course_id = request.form["course_id"]

    error = validate_student_data(cursor, name, dob, gender, contact, course_id, student_id=student_id)
    if error:
        cursor.close()
        conn.close()
        return error

    cursor.execute(
        "UPDATE students SET name=%s, dob=%s, gender=%s, contact=%s, course_id=%s WHERE student_id=%s",
        (name.strip(), dob, gender, contact.strip(), course_id, student_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")


# ── Delete (POST only — prevents accidental/crawler deletion) ─────────────────

@app.route("/delete/<int:student_id>", methods=["POST"])
def delete(student_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")


# ── Courses ───────────────────────────────────────────────────────────────────

@app.route("/courses")
def course_page():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("courses.html", courses=courses)


@app.route("/courses/add", methods=["POST"])
def add_course():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    name = request.form["course_name"].strip()

    # Empty course name
    if not name:
        cursor.close()
        conn.close()
        return "Course name cannot be empty."

    # Only letters and spaces allowed
    if not name.replace(" ", "").isalpha():
        cursor.close()
        conn.close()
        return "Course name should contain only alphabets."

    # Prevent duplicate course names (case-insensitive)
    cursor.execute(
        "SELECT * FROM courses WHERE LOWER(course_name)=LOWER(%s)",
        (name,)
    )

    if cursor.fetchone():
        cursor.close()
        conn.close()
        return "Course already exists."

    # Insert the course
    cursor.execute(
        "INSERT INTO courses (course_name) VALUES (%s)",
        (name.title(),)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/courses")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM courses")
    total_courses = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT s.name, c.course_name, s.dob
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.course_id
        ORDER BY s.student_id DESC LIMIT 5
    """)
    recent = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("dashboard.html",
                            total_students=total_students,
                            total_courses=total_courses,
                            recent_students=recent)


# ── Other pages ───────────────────────────────────────────────────────────────

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
