"""
database.py - Local Database cho Parent Academic Agent (using SQLite)
=====================================================================
Load dữ liệu học sinh từ database SQLite.

Cấu trúc:
  - Mỗi học sinh có thể có nhiều dòng (1 dòng / năm học).
  - Dữ liệu điểm factor_1 dạng CSV string (nhiều điểm, phân cách bằng dấu ",").
  - Dữ liệu điểm factor_2 và factor_3 là số đơn lẻ.

Helper functions:
  get_student(student_id)
  get_grades(student_id, academic_year=None, subject=None)
  get_conduct(student_id, academic_year=None)
  lookup_student_by_name(name)         - tìm kiếm mờ (fuzzy) không dấu
  get_all_years(student_id)            - lấy danh sách năm học của học sinh
"""

import sqlite3
import os
import unicodedata
from typing import Dict, Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Đường dẫn tuyệt đối tới SQLite database
# ---------------------------------------------------------------------------
_DB_PATH = os.path.join(
    os.path.dirname(__file__),  # src/data/
    "..", "..", "data", "students.db"
)
_DB_PATH = os.path.normpath(_DB_PATH)

# ---------------------------------------------------------------------------
# Danh sách 8 môn học (tên tiếng Anh)
# ---------------------------------------------------------------------------
SUBJECTS = [
    "Math", "Literature", "English", "Physics",
    "Chemistry", "Biology", "History", "Geography"
]

# ---------------------------------------------------------------------------
# Ánh xạ tên môn tiếng Việt -> key tiếng Anh (dùng cho fuzzy lookup)
# ---------------------------------------------------------------------------
SUBJECT_ALIASES: Dict[str, str] = {
    # Toán
    "toan": "Math", "math": "Math", "mathematics": "Math",
    # Văn / Ngữ văn
    "van": "Literature", "ngu van": "Literature", "literature": "Literature",
    # Anh / Tiếng Anh
    "anh": "English", "tieng anh": "English", "english": "English",
    # Lý / Vật lý
    "ly": "Physics", "vat ly": "Physics", "physics": "Physics",
    # Hóa / Hóa học
    "hoa": "Chemistry", "hoa hoc": "Chemistry", "chemistry": "Chemistry",
    # Sinh / Sinh học
    "sinh": "Biology", "sinh hoc": "Biology", "biology": "Biology",
    # Sử / Lịch sử
    "su": "History", "lich su": "History", "history": "History",
    # Địa / Địa lý
    "dia": "Geography", "dia ly": "Geography", "geography": "Geography",
}


# ===========================================================================
# Parser nội bộ
# ===========================================================================

def _parse_factor_list(raw: Optional[str]) -> List[float]:
    """Parse comma-separated factor list from DB"""
    if raw is None:
        return []
    if isinstance(raw, (int, float)):
        # If it's a single number, return it as a list with one element
        return [float(raw)]
    if not raw or raw.strip() == "":
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    result = []
    for p in parts:
        try:
            result.append(float(p))
        except ValueError:
            pass
    return result


def _remove_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để so sánh không dấu."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    result = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return result.lower().strip()


# ===========================================================================
# Database helpers
# ===========================================================================
def get_db_connection():
    """Helper to get database connection"""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
# Public API
# ===========================================================================

def get_student(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin học sinh (năm học mới nhất).

    Args:
        student_id: Mã học sinh, vd "S001".

    Returns:
        Dict thông tin học sinh hoặc None nếu không tìm thấy.
    """
    sid = student_id.strip().upper()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Get latest academic year for this student
        cursor.execute(
            "SELECT * FROM students WHERE student_id = ? ORDER BY academic_year DESC LIMIT 1",
            (sid,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_student_by_parent_phone(parent_phone: str, academic_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin học sinh theo số điện thoại phụ huynh (năm học mới nhất nếu không chỉ định).

    Args:
        parent_phone: Số điện thoại phụ huynh.
        academic_year: Năm học (nếu None -> lấy năm mới nhất).

    Returns:
        Dict thông tin học sinh hoặc None nếu không tìm thấy.
    """
    phone = parent_phone.strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if academic_year:
            cursor.execute(
                "SELECT * FROM students WHERE parent_phone = ? AND academic_year = ? LIMIT 1",
                (phone, academic_year)
            )
        else:
            cursor.execute(
                "SELECT * FROM students WHERE parent_phone = ? ORDER BY academic_year DESC LIMIT 1",
                (phone,)
            )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_student_by_name_and_phone(name: str, parent_phone: str, academic_year: Optional[str] = None, grade_level: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Tìm học sinh bằng cả tên và số điện thoại phụ huynh (fuzzy matching cho tên).

    Args:
        name: Tên học sinh (có thể gõ sai dấu / viết tắt).
        parent_phone: Số điện thoại phụ huynh.
        academic_year: Năm học (nếu None -> lấy năm mới nhất).
        grade_level: Lớp học cần tìm (ví dụ: "10", "11", "12").

    Returns:
        Dict thông tin học sinh hoặc None nếu không tìm thấy.
    """
    phone = parent_phone.strip()
    query_name = _remove_accents(name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if academic_year:
            cursor.execute(
                "SELECT * FROM students WHERE parent_phone = ? AND academic_year = ?",
                (phone, academic_year)
            )
        elif grade_level:
            cursor.execute(
                "SELECT * FROM students WHERE parent_phone = ? AND grade_level = ?",
                (phone, str(grade_level).strip())
            )
        else:
            cursor.execute(
                "SELECT * FROM students WHERE parent_phone = ? ORDER BY academic_year DESC",
                (phone,)
            )
        rows = cursor.fetchall()
        for row in rows:
            student_name_clean = _remove_accents(row["name"])
            if query_name in student_name_clean or student_name_clean in query_name:
                return dict(row)
        return None
    finally:
        conn.close()


def get_student_grades_list_by_phone(parent_phone: str, name: str) -> List[Dict[str, Any]]:
    """
    Lấy danh sách tất cả các dòng điểm (tất cả các lớp) của học sinh khớp với tên và số điện thoại phụ huynh.

    Args:
        parent_phone: Số điện thoại phụ huynh.
        name: Tên học sinh.

    Returns:
        List các dòng điểm tương ứng.
    """
    phone = parent_phone.strip()
    query_name = _remove_accents(name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM students WHERE parent_phone = ? ORDER BY grade_level ASC",
            (phone,)
        )
        rows = cursor.fetchall()
        matches = []
        for row in rows:
            student_name_clean = _remove_accents(row["name"])
            if query_name in student_name_clean or student_name_clean in query_name:
                matches.append(dict(row))
        return matches
    finally:
        conn.close()



def get_student_by_grade_level(student_id: str, grade_level: str) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin học sinh tại một lớp cụ thể (grade_level: "10", "11", "12").

    Args:
        student_id: Mã học sinh.
        grade_level: Lớp cần tìm (vd "11").

    Returns:
        Dict thông tin học sinh hoặc None nếu không tìm thấy.
    """
    sid = student_id.strip().upper()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM students WHERE student_id = ? AND grade_level = ?",
            (sid, grade_level)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_all_years(student_id: str) -> List[str]:
    """
    Lấy danh sách tất cả các năm học của một học sinh.

    Args:
        student_id: Mã học sinh.

    Returns:
        List năm học đã sắp xếp, vd ["2023-2024", "2024-2025", "2025-2026"].
    """
    sid = student_id.strip().upper()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT academic_year FROM students WHERE student_id = ? ORDER BY academic_year ASC",
            (sid,)
        )
        rows = cursor.fetchall()
        return [row["academic_year"] for row in rows]
    finally:
        conn.close()


def get_latest_year(student_id: str) -> Optional[str]:
    """Trả về năm học mới nhất của học sinh."""
    years = get_all_years(student_id)
    return years[-1] if years else None


def get_grades(
    student_id: str,
    academic_year: Optional[str] = None,
    subject: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Lấy điểm số học sinh.

    Args:
        student_id: Mã học sinh.
        academic_year: Năm học, vd "2025-2026". Nếu None -> dùng năm mới nhất.
        subject: Tên môn tiếng Anh, vd "Math". Nếu None -> trả về tất cả 8 môn.

    Returns:
        - Nếu subject được chỉ định: Dict điểm môn đó {"factor_1", "factor_2", "factor_3", "gpa"}.
        - Nếu subject=None: Dict toàn bộ 8 môn.
        - None nếu không tìm thấy.
    """
    sid = student_id.strip().upper()
    year = academic_year or get_latest_year(sid)
    if not year:
        return None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM students WHERE student_id = ? AND academic_year = ?",
            (sid, year)
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Build grades dict
        subject_grades = {}
        for subj in SUBJECTS:
            f1_raw = row[f"{subj}_factor_1"]
            f2_raw = row[f"{subj}_factor_2"]
            factor_1 = _parse_factor_list(f1_raw)
            factor_2 = _parse_factor_list(f2_raw)
            factor_3 = row[f"{subj}_factor_3"]
            gpa = row[f"{subj}_gpa"]
            subject_grades[subj] = {
                "factor_1": factor_1,
                "factor_2": factor_2,
                "factor_3": factor_3,
                "gpa": gpa,
            }

        if subject:
            # Resolve alias
            subj_key = resolve_subject(subject)
            if subj_key is None:
                return None
            return subject_grades.get(subj_key)

        return subject_grades
    finally:
        conn.close()


def get_conduct(
    student_id: str,
    academic_year: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin hạnh kiểm & chuyên cần.

    Args:
        student_id: Mã học sinh.
        academic_year: Năm học. Nếu None -> dùng năm mới nhất.

    Returns:
        Dict hạnh kiểm hoặc None nếu không tìm thấy.
    """
    sid = student_id.strip().upper()
    year = academic_year or get_latest_year(sid)
    if not year:
        return None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM students WHERE student_id = ? AND academic_year = ?",
            (sid, year)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "excused_absences": row["excused_absences"],
            "unexcused_absences": row["unexcused_absences"],
            "behavior_score": row["behavior_score"],
            "conduct_grade": row["conduct_grade"],
            "teacher_remarks": row["teacher_remarks"],
            "overall_gpa": row["overall_gpa"],
        }
    finally:
        conn.close()


def lookup_student_by_name(name: str) -> List[Dict[str, Any]]:
    """
    Tìm học sinh theo tên (fuzzy matching, không phân biệt hoa thường & dấu).

    Args:
        name: Tên cần tìm (có thể nhập sai dấu / viết tắt).

    Returns:
        Danh sách các học sinh khớp (có thể rỗng hoặc nhiều kết quả).
        Mỗi phần tử là Dict {"student_id", "name", "class", ...}.
    """
    query = _remove_accents(name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Get all unique students (latest year), then filter by name
        cursor.execute("""
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER(PARTITION BY student_id ORDER BY academic_year DESC) AS rn
                FROM students
            )
            SELECT * FROM ranked WHERE rn = 1
        """)
        rows = cursor.fetchall()
        results = []
        seen = set()
        for row in rows:
            sid = row["student_id"]
            if sid in seen:
                continue
            student_name_clean = _remove_accents(row["name"])
            # Khớp nếu query là chuỗi con của tên học sinh
            if query in student_name_clean or student_name_clean in query:
                results.append(dict(row))
                seen.add(sid)
        return results
    finally:
        conn.close()


def resolve_subject(subject_input: str) -> Optional[str]:
    """
    Resolve tên môn học từ tiếng Việt hoặc tiếng Anh sang key chuẩn.

    Args:
        subject_input: Tên môn học (tiếng Anh hoặc tiếng Việt).

    Returns:
        Key chuẩn (vd "Math") hoặc None nếu không nhận dạng được.
    """
    if not subject_input:
        return None

    # Thử khớp chính xác trước
    for subj in SUBJECTS:
        if subject_input.strip().lower() == subj.lower():
            return subj

    # Thử qua alias (đã loại dấu)
    key = _remove_accents(subject_input)
    return SUBJECT_ALIASES.get(key)


def compute_gpa(grades_dict: Dict[str, Any]) -> Optional[float]:
    """
    Tính lại GPA môn theo công thức:
      GPA = (Σ factor_1 * 1 + Σ factor_2 * 2 + factor_3 * 3)
            / (count_f1 * 1 + count_f2 * 2 + 1 * 3)

    Args:
        grades_dict: {"factor_1": [...], "factor_2": [...], "factor_3": float}

    Returns:
        GPA tính được hoặc None nếu dữ liệu không đủ.
    """
    f1 = grades_dict.get("factor_1") or []
    f2 = grades_dict.get("factor_2") or []
    f3 = grades_dict.get("factor_3")

    if f3 is None:
        return None

    total_score = sum(f1) * 1 + sum(f2) * 2 + f3 * 3
    total_weight = len(f1) * 1 + len(f2) * 2 + 1 * 3

    if total_weight == 0:
        return None

    return round(total_score / total_weight, 2)


def compute_overall_gpa(student_id: str, academic_year: Optional[str] = None) -> Optional[float]:
    """
    Tính GPA tổng hợp của học sinh từ GPA 8 môn (trung bình cộng đơn giản).

    Args:
        student_id: Mã học sinh.
        academic_year: Năm học (None -> mới nhất).

    Returns:
        GPA tổng hợp hoặc None.
    """
    grades = get_grades(student_id, academic_year)
    if not grades:
        return None

    gpa_list = []
    for subj in SUBJECTS:
        subj_grades = grades.get(subj, {})
        gpa = subj_grades.get("gpa")
        if gpa is not None:
            gpa_list.append(gpa)

    if not gpa_list:
        return None

    return round(sum(gpa_list) / len(gpa_list), 2)


def get_full_report(
    student_id: str,
    academic_year: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Lấy báo cáo toàn diện của học sinh: thông tin + điểm + hạnh kiểm.

    Args:
        student_id: Mã học sinh.
        academic_year: Năm học (None -> mới nhất).

    Returns:
        Dict đầy đủ hoặc None nếu không tìm thấy.
    """
    sid = student_id.strip().upper()
    year = academic_year or get_latest_year(sid)

    student = get_student(sid)
    if student is None:
        return None

    grades = get_grades(sid, year)
    conduct = get_conduct(sid, year)

    # Tính GPA từng môn (có thể dùng giá trị sẵn trong CSV)
    subject_summary = {}
    weak_subjects = []
    if grades:
        for subj in SUBJECTS:
            subj_data = grades.get(subj, {})
            gpa = subj_data.get("gpa") or compute_gpa(subj_data)
            subject_summary[subj] = {
                "gpa": gpa,
                "factor_1": subj_data.get("factor_1", []),
                "factor_2": subj_data.get("factor_2", []),
                "factor_3": subj_data.get("factor_3"),
            }
            if gpa is not None and gpa < 5.0:
                weak_subjects.append(subj)

    overall_gpa = conduct.get("overall_gpa") if conduct else compute_overall_gpa(sid, year)

    return {
        "student_id": sid,
        "name": student["name"],
        "academic_year": year,
        "class": student.get("class"),
        "grade_level": student.get("grade_level"),
        "parent": student.get("parent"),
        "parent_phone": student.get("parent_phone"),
        "email": student.get("email"),
        "subjects": subject_summary,
        "overall_gpa": overall_gpa,
        "weak_subjects": weak_subjects,
        "conduct": conduct,
    }


# ===========================================================================
# Stats & Utilities
# ===========================================================================

def get_stats() -> Dict[str, Any]:
    """Trả về thống kê tổng quan về database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT student_id) FROM students")
        total_students = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM students")
        total_records = cursor.fetchone()[0]
        cursor.execute("SELECT DISTINCT student_id FROM students LIMIT 5")
        sample_ids = [row[0] for row in cursor.fetchall()]
        return {
            "total_students": total_students,
            "total_records": total_records,
            "subjects": SUBJECTS,
            "sample_ids": sample_ids,
        }
    finally:
        conn.close()
