"""
academic_tools.py - Bộ công cụ tra cứu học tập cho ReAct Agent
================================================================
Gồm đầy đủ 4 công cụ theo PRD:

  1. lookup_student_id(name)           - Tìm mã học sinh theo tên (fuzzy matching)
  2. get_academic_grades(student_id,   - Lấy điểm + GPA theo môn hoặc toàn bộ
                         subject,
                         academic_year)
  3. get_conduct_report(student_id,    - Báo cáo chuyên cần & hạnh kiểm
                        academic_year)
  4. generate_study_advice(student_id) - (Bonus) Tư vấn cải thiện học tập

Mỗi tool trả về JSON string để agent đưa vào Observation.
"""

import json
from typing import Optional
from datetime import datetime

from src.data.database import (
    get_student,
    get_student_by_parent_phone,
    get_student_by_name_and_phone,
    get_student_grades_list_by_phone,
    get_student_by_grade_level,
    get_grades,
    get_conduct,
    get_full_report,
    get_all_years,
    get_latest_year,
    lookup_student_by_name,
    resolve_subject,
    compute_gpa,
    compute_overall_gpa,
    SUBJECTS,
)


# ===========================================================================
# Helper
# ===========================================================================

def _ts() -> str:
    return datetime.now().isoformat()


def _ok(tool: str, data: dict) -> str:
    """Wrap kết quả thành JSON string chuẩn."""
    return json.dumps(
        {"status": "success", "tool": tool, "timestamp": _ts(), **data},
        ensure_ascii=False,
        indent=2
    )


def _err(tool: str, message: str) -> str:
    """Wrap lỗi thành JSON string chuẩn."""
    return json.dumps(
        {"status": "error", "tool": tool, "timestamp": _ts(), "message": message},
        ensure_ascii=False,
        indent=2
    )


# ===========================================================================
# Tool 1 - lookup_student_id
# ===========================================================================

def lookup_student_id(student_name: str) -> str:
    """
    Tìm mã học sinh theo tên (có hỗ trợ tìm kiếm mờ, không phân biệt dấu).

    Args:
        student_name: Tên học sinh cần tìm (có thể viết tắt hoặc thiếu dấu).
                      Ví dụ: "giang", "Lý Duy Giang", "ly duy giang"

    Returns:
        JSON string chứa student_id và thông tin cơ bản.
        Nếu nhiều kết quả, trả về danh sách để agent chọn đúng.
        Nếu không tìm thấy, trả về lỗi có gợi ý.
    """
    if not student_name or not student_name.strip():
        return _err("lookup_student_id", "Tên học sinh không được để trống.")

    matches = lookup_student_by_name(student_name.strip())

    if not matches:
        return _err(
            "lookup_student_id",
            f"Không tìm thấy học sinh nào có tên chứa '{student_name}'. "
            "Hãy kiểm tra lại tên hoặc thử tìm bằng mã học sinh trực tiếp."
        )

    if len(matches) == 1:
        s = matches[0]
        return _ok("lookup_student_id", {
            "found": True,
            "student_id": s["student_id"],
            "name": s["name"],
            "class": s["class"],
            "grade_level": s["grade_level"],
            "parent": s["parent"],
            "parent_phone": s["parent_phone"],
            "latest_year": get_latest_year(s["student_id"]),
            "all_years": get_all_years(s["student_id"]),
        })

    # Nhiều kết quả
    candidates = [
        {
            "student_id": s["student_id"],
            "name": s["name"],
            "class": s["class"],
            "grade_level": s["grade_level"],
        }
        for s in matches
    ]
    return _ok("lookup_student_id", {
        "found": True,
        "multiple_matches": True,
        "message": (
            f"Tìm thấy {len(matches)} học sinh có tên chứa '{student_name}'. "
            "Vui lòng chỉ định student_id chính xác hơn."
        ),
        "candidates": candidates,
    })


# ===========================================================================
# Tool 2 - get_academic_grades
# ===========================================================================

def get_academic_grades(
    student_id: str,
    subject: str = "All",
    academic_year: Optional[str] = None
) -> str:
    """
    Lấy điểm số và GPA của học sinh theo môn học.

    Args:
        student_id: Mã học sinh, vd "S001".
        subject: Tên môn học (tiếng Anh hoặc tiếng Việt), hoặc "All" để lấy tất cả.
                 Giá trị hợp lệ: Math, Literature, English, Physics, Chemistry,
                                  Biology, History, Geography, All
                 Hoặc tiếng Việt: Toán, Văn, Anh, Lý, Hóa, Sinh, Sử, Địa
        academic_year: Năm học, vd "2025-2026". Nếu None → dùng năm mới nhất.

    Returns:
        JSON string chứa điểm factor_1, factor_2, factor_3 và GPA môn,
        cùng cảnh báo học lực nếu GPA < 5.0.
    """
    sid = student_id.strip().upper()

    student = get_student(sid)
    if student is None:
        return _err("get_academic_grades", f"Không tìm thấy học sinh có mã '{sid}'.")

    year = academic_year or get_latest_year(sid)
    if not year:
        return _err("get_academic_grades", f"Không có dữ liệu năm học cho học sinh '{sid}'.")

    # --- Lấy toàn bộ môn ---
    if subject.strip().lower() in ("all", "tat ca", "tất cả", ""):
        grades = get_grades(sid, year)
        if grades is None:
            return _err("get_academic_grades",
                        f"Không có dữ liệu điểm năm {year} cho học sinh '{sid}'.")

        subject_summary = {}
        weak_subjects = []
        for subj in SUBJECTS:
            subj_data = grades.get(subj, {})
            gpa = subj_data.get("gpa") or compute_gpa(subj_data)
            subject_summary[subj] = {
                "factor_1": subj_data.get("factor_1", []),
                "factor_2": subj_data.get("factor_2", []),
                "factor_3": subj_data.get("factor_3"),
                "gpa": gpa,
            }
            if gpa is not None and gpa < 5.0:
                weak_subjects.append(subj)

        conduct = get_conduct(sid, year)
        overall_gpa = (conduct or {}).get("overall_gpa") or compute_overall_gpa(sid, year)

        return _ok("get_academic_grades", {
            "student_id": sid,
            "name": student["name"],
            "class": student["class"],
            "academic_year": year,
            "subjects": subject_summary,
            "overall_gpa": overall_gpa,
            "weak_subjects": weak_subjects,
            "alert": (
                f"CANH BAO: Hoc sinh co {len(weak_subjects)} mon duoi trung binh: "
                f"{', '.join(weak_subjects)}"
                if weak_subjects else None
            ),
        })

    # --- Lấy một môn cụ thể ---
    subj_key = resolve_subject(subject)
    if subj_key is None:
        return _err(
            "get_academic_grades",
            f"Môn học '{subject}' không hợp lệ. "
            f"Vui lòng dùng một trong: {', '.join(SUBJECTS)} "
            f"hoặc tương đương tiếng Việt: Toán, Văn, Anh, Lý, Hóa, Sinh, Sử, Địa."
        )

    grades = get_grades(sid, year)
    if grades is None:
        return _err("get_academic_grades",
                    f"Không có dữ liệu điểm năm {year} cho học sinh '{sid}'.")

    subj_data = grades.get(subj_key, {})
    gpa = subj_data.get("gpa") or compute_gpa(subj_data)

    return _ok("get_academic_grades", {
        "student_id": sid,
        "name": student["name"],
        "class": student["class"],
        "academic_year": year,
        "subject": subj_key,
        "factor_1": subj_data.get("factor_1", []),
        "factor_2": subj_data.get("factor_2", []),
        "factor_3": subj_data.get("factor_3"),
        "gpa": gpa,
        "alert": (
            f"CANH BAO: Diem mon {subj_key} dang duoi trung binh (GPA = {gpa})!"
            if gpa is not None and gpa < 5.0 else None
        ),
    })


# ===========================================================================
# Tool 3 - get_conduct_report
# ===========================================================================

def get_conduct_report(
    student_id: str,
    academic_year: Optional[str] = None
) -> str:
    """
    Lấy báo cáo chuyên cần và hạnh kiểm của học sinh.

    Args:
        student_id: Mã học sinh.
        academic_year: Năm học (None → mới nhất).

    Returns:
        JSON string chứa số buổi nghỉ có phép / không phép, điểm hạnh kiểm,
        xếp loại hạnh kiểm, nhận xét GVCN và GPA tổng hợp.
        Tự động gắn cảnh báo đỏ nếu nghỉ không phép > 3 buổi.
    """
    sid = student_id.strip().upper()

    student = get_student(sid)
    if student is None:
        return _err("get_conduct_report", f"Không tìm thấy học sinh có mã '{sid}'.")

    year = academic_year or get_latest_year(sid)
    if not year:
        return _err("get_conduct_report", f"Không có dữ liệu năm học cho học sinh '{sid}'.")

    conduct = get_conduct(sid, year)
    if conduct is None:
        return _err("get_conduct_report",
                    f"Không có dữ liệu hạnh kiểm năm {year} cho học sinh '{sid}'.")

    unexcused = conduct.get("unexcused_absences") or 0
    excused = conduct.get("excused_absences") or 0
    total_absences = excused + unexcused

    # Cảnh báo kỷ luật nếu nghỉ không phép > 3 buổi
    discipline_alert = None
    if unexcused > 3:
        discipline_alert = (
            f"CANH BAO DO: Hoc sinh nghi khong phep {unexcused} buoi "
            f"(nguong nguy hiem > 3 buoi). Can gia dinh phoi hop xu ly gap!"
        )

    return _ok("get_conduct_report", {
        "student_id": sid,
        "name": student["name"],
        "class": student["class"],
        "academic_year": year,
        "excused_absences": excused,
        "unexcused_absences": unexcused,
        "total_absences": total_absences,
        "behavior_score": conduct.get("behavior_score"),
        "conduct_grade": conduct.get("conduct_grade"),
        "overall_gpa": conduct.get("overall_gpa"),
        "teacher_remarks": conduct.get("teacher_remarks"),
        "discipline_alert": discipline_alert,
        "all_years_available": get_all_years(sid),
    })


# ===========================================================================
# Tool 4 (Bonus) - generate_study_advice
# ===========================================================================

def generate_study_advice(student_id: str) -> str:
    """
    (Bonus Tool) Phân tích học lực và đưa ra lời khuyên cải thiện học tập.

    Dựa trên:
    - Môn học có GPA thấp nhất
    - Xu hướng GPA qua các năm học
    - Nhận xét của GVCN
    - Tỷ lệ chuyên cần

    Args:
        student_id: Mã học sinh.

    Returns:
        JSON string chứa phân tích toàn diện và lộ trình cải thiện.
    """
    sid = student_id.strip().upper()

    student = get_student(sid)
    if student is None:
        return _err("generate_study_advice", f"Không tìm thấy học sinh có mã '{sid}'.")

    all_years = get_all_years(sid)
    if not all_years:
        return _err("generate_study_advice", f"Không có dữ liệu năm học cho '{sid}'.")

    latest_year = all_years[-1]

    # Lấy báo cáo năm mới nhất
    report = get_full_report(sid, latest_year)
    if report is None:
        return _err("generate_study_advice", f"Không có đủ dữ liệu để tư vấn cho '{sid}'.")

    subjects_data = report.get("subjects", {})
    conduct_data = report.get("conduct", {})

    # Xếp hạng môn học theo GPA (từ thấp đến cao)
    subject_ranking = []
    for subj in SUBJECTS:
        gpa = (subjects_data.get(subj) or {}).get("gpa")
        if gpa is not None:
            subject_ranking.append((subj, gpa))
    subject_ranking.sort(key=lambda x: x[1])

    weakest = subject_ranking[:3] if subject_ranking else []
    strongest = subject_ranking[-3:] if subject_ranking else []

    # Xu hướng GPA qua các năm
    gpa_trend = []
    for yr in all_years:
        c = get_conduct(sid, yr)
        if c:
            gpa_trend.append({"year": yr, "overall_gpa": c.get("overall_gpa")})

    # Chuyên cần
    unexcused = conduct_data.get("unexcused_absences", 0) or 0
    attendance_advice = None
    if unexcused > 3:
        attendance_advice = (
            f"Hoc sinh da nghi khong phep {unexcused} buoi. "
            "Viec di hoc day du la yeu to then chot de cai thien ket qua. "
            "Can gia dinh theo doi chat che hon."
        )

    # Lời khuyên theo từng môn yếu
    advice_per_subject = []
    SUBJECT_TIPS = {
        "Math": "Nen lam them bai tap toan tu giai va hoc them gia su neu can.",
        "Literature": "Doc them sach van hoc, luyen viet van nghi luan va phan tich tho van.",
        "English": "Luyen nghe, noi tieng Anh hang ngay qua cac ung dung va video.",
        "Physics": "Hoc ki cong thuc va luyen nhieu dang bai tap ap dung vao thuc te.",
        "Chemistry": "Hieu ro ban chat phan ung hoa hoc truoc khi lam bai tap.",
        "Biology": "Doc ky SGK, ve so do tu duy de ghi nho kien thuc sinh hoc.",
        "History": "Hoc su theo duong thoi gian, su dung so do Mindmap de ghi nho.",
        "Geography": "Luyen doc ban do va hieu ro dia hinh, khi hau cac vung.",
    }
    for subj, gpa in weakest:
        advice_per_subject.append({
            "subject": subj,
            "current_gpa": gpa,
            "advice": SUBJECT_TIPS.get(subj, "Can dau tu them thoi gian hoc tap mon nay."),
            "priority": "CAO" if gpa < 5.0 else "TRUNG BINH",
        })

    overall_gpa = report.get("overall_gpa")
    if overall_gpa is not None:
        if overall_gpa >= 8.5:
            overall_assessment = "Hoc luc Gioi - Duy tri va phat huy!"
        elif overall_gpa >= 7.0:
            overall_assessment = "Hoc luc Kha - Co the phan dau dat Gioi neu co gang them."
        elif overall_gpa >= 5.0:
            overall_assessment = "Hoc luc Trung binh - Can co gang nhieu hon, dac biet cac mon yeu."
        else:
            overall_assessment = "Hoc luc Yeu - Can su phoi hop gap gap giua gia dinh va nha truong."
    else:
        overall_assessment = "Chua du du lieu de danh gia."

    return _ok("generate_study_advice", {
        "student_id": sid,
        "name": student["name"],
        "class": student["class"],
        "academic_year": latest_year,
        "overall_gpa": overall_gpa,
        "overall_assessment": overall_assessment,
        "gpa_trend": gpa_trend,
        "weakest_subjects": [{"subject": s, "gpa": g} for s, g in weakest],
        "strongest_subjects": [{"subject": s, "gpa": g} for s, g in strongest],
        "improvement_plan": advice_per_subject,
        "attendance_advice": attendance_advice,
        "teacher_remarks": conduct_data.get("teacher_remarks"),
        "conduct_grade": conduct_data.get("conduct_grade"),
    })


# ===========================================================================
# Tool 5 - verify_parent_phone
# ===========================================================================

def verify_parent_phone(parent_phone: str, grade_level: Optional[str] = None) -> str:
    """
    Xác thực số điện thoại phụ huynh và trả về thông tin học sinh tương ứng.

    Args:
        parent_phone: Số điện thoại phụ huynh.
        grade_level: Lớp cần tra cứu (tùy chọn).

    Returns:
        JSON string chứa thông tin học sinh nếu số điện thoại hợp lệ,
        hoặc thông báo nhiều lớp học để Agent hỏi lại người dùng.
    """
    if not parent_phone or not parent_phone.strip():
        return _err("verify_parent_phone", "Số điện thoại không được để trống.")

    phone = parent_phone.strip()
    
    # Get the latest row just to find the student name associated with this phone
    student = get_student_by_parent_phone(phone)
    if not student:
        return _err(
            "verify_parent_phone",
            f"Không tìm thấy học sinh nào có số điện thoại phụ huynh '{parent_phone}'. "
            "Vui lòng kiểm tra lại số điện thoại."
        )

    # Check for multiple grades using the student name and phone
    matches = get_student_grades_list_by_phone(phone, student["name"])
    
    # If grade level is specified
    if grade_level:
        gl_str = str(grade_level).strip()
        for m in matches:
            if m["grade_level"] == gl_str:
                return _ok("verify_parent_phone", {
                    "student_id": m["student_id"],
                    "name": m["name"],
                    "class": m["class"],
                    "grade_level": m["grade_level"],
                    "academic_year": m["academic_year"],
                    "parent_phone": phone,
                    "multiple_grades": False
                })
        return _err(
            "verify_parent_phone",
            f"Tìm thấy học sinh '{student['name']}' nhưng không có dữ liệu lớp '{grade_level}'."
        )

    # If no grade level is specified, and we have multiple matches
    if len(matches) > 1:
        grades = [m["grade_level"] for m in matches]
        return _ok("verify_parent_phone", {
            "student_id": matches[0]["student_id"],
            "name": matches[0]["name"],
            "parent_phone": phone,
            "multiple_grades": True,
            "available_grades": grades,
            "message": f"Tìm thấy điểm của học sinh {matches[0]['name']} ở các lớp: {', '.join(['lớp ' + g for g in grades])}. Bạn muốn tìm điểm của học sinh {matches[0]['name']} lớp mấy?"
        })

    # Only one match
    m = matches[0]
    return _ok("verify_parent_phone", {
        "student_id": m["student_id"],
        "name": m["name"],
        "class": m["class"],
        "grade_level": m["grade_level"],
        "academic_year": m["academic_year"],
        "parent_phone": phone,
        "multiple_grades": False
    })


# ===========================================================================
# Tool 6 - search_student_by_name_and_phone
# ===========================================================================

def search_student_by_name_and_phone(name: str, parent_phone: str, grade_level: Optional[str] = None) -> str:
    """
    Tìm học sinh chính xác bằng cả tên và số điện thoại phụ huynh.

    Args:
        name: Tên học sinh (fuzzy matching hỗ trợ).
        parent_phone: Số điện thoại phụ huynh.
        grade_level: Lớp học cần tra cứu (tùy chọn).

    Returns:
        JSON string chứa thông tin học sinh chính xác.
    """
    if not name or not name.strip():
        return _err("search_student_by_name_and_phone", "Tên học sinh không được để trống.")
    if not parent_phone or not parent_phone.strip():
        return _err("search_student_by_name_and_phone", "Số điện thoại phụ huynh không được để trống.")

    phone = parent_phone.strip()
    matches = get_student_grades_list_by_phone(phone, name.strip())

    if not matches:
        return _err(
            "search_student_by_name_and_phone",
            f"Không tìm thấy học sinh nào có tên '{name}' và số điện thoại phụ huynh '{parent_phone}'. "
            "Vui lòng kiểm tra lại thông tin."
        )

    # If grade level is specified, try to find the match
    if grade_level:
        gl_str = str(grade_level).strip()
        for m in matches:
            if m["grade_level"] == gl_str:
                return _ok("search_student_by_name_and_phone", {
                    "student_id": m["student_id"],
                    "name": m["name"],
                    "class": m["class"],
                    "grade_level": m["grade_level"],
                    "academic_year": m["academic_year"],
                    "parent_phone": phone,
                    "multiple_grades": False
                })
        return _err(
            "search_student_by_name_and_phone",
            f"Tìm thấy học sinh '{matches[0]['name']}' nhưng không có dữ liệu lớp '{grade_level}'."
        )

    # If no grade level is specified, and we have multiple matches
    if len(matches) > 1:
        grades = [m["grade_level"] for m in matches]
        return _ok("search_student_by_name_and_phone", {
            "student_id": matches[0]["student_id"],
            "name": matches[0]["name"],
            "parent_phone": phone,
            "multiple_grades": True,
            "available_grades": grades,
            "message": f"Tìm thấy điểm của học sinh {matches[0]['name']} ở các lớp: {', '.join(['lớp ' + g for g in grades])}. Bạn muốn tìm điểm của học sinh {matches[0]['name']} lớp mấy?"
        })

    # Only one match
    m = matches[0]
    return _ok("search_student_by_name_and_phone", {
        "student_id": m["student_id"],
        "name": m["name"],
        "class": m["class"],
        "grade_level": m["grade_level"],
        "academic_year": m["academic_year"],
        "parent_phone": phone,
        "multiple_grades": False
    })



# ===========================================================================
# Tool 7 - get_grades_by_grade_level
# ===========================================================================

def get_grades_by_grade_level(
    student_id: str,
    grade_level: str,
    subject: str = "All"
) -> str:
    """
    Lấy điểm số của học sinh tại một lớp cụ thể (grade level như "10", "11", "12").

    Args:
        student_id: Mã học sinh.
        grade_level: Lớp cần tra cứu (vd "11").
        subject: Tên môn học hoặc "All".

    Returns:
        JSON string chứa điểm số tại lớp cụ thể.
    """
    sid = student_id.strip().upper()
    gl = str(grade_level).strip()

    student = get_student_by_grade_level(sid, gl)
    if not student:
        return _err(
            "get_grades_by_grade_level",
            f"Không tìm thấy dữ liệu cho học sinh '{sid}' tại lớp '{gl}'."
        )

    year = student["academic_year"]

    # --- Lấy toàn bộ môn ---
    if subject.strip().lower() in ("all", "tat ca", "tất cả", ""):
        grades = get_grades(sid, year)
        if grades is None:
            return _err("get_grades_by_grade_level",
                        f"Không có dữ liệu điểm năm {year} cho học sinh '{sid}'.")

        subject_summary = {}
        weak_subjects = []
        for subj in SUBJECTS:
            subj_data = grades.get(subj, {})
            gpa = subj_data.get("gpa") or compute_gpa(subj_data)
            subject_summary[subj] = {
                "factor_1": subj_data.get("factor_1", []),
                "factor_2": subj_data.get("factor_2", []),
                "factor_3": subj_data.get("factor_3"),
                "gpa": gpa,
            }
            if gpa is not None and gpa < 5.0:
                weak_subjects.append(subj)

        conduct = get_conduct(sid, year)
        overall_gpa = (conduct or {}).get("overall_gpa") or compute_overall_gpa(sid, year)

        return _ok("get_grades_by_grade_level", {
            "student_id": sid,
            "name": student["name"],
            "class": student["class"],
            "grade_level": gl,
            "academic_year": year,
            "subjects": subject_summary,
            "overall_gpa": overall_gpa,
            "weak_subjects": weak_subjects,
            "alert": (
                f"CANH BAO: Hoc sinh co {len(weak_subjects)} mon duoi trung binh: "
                f"{', '.join(weak_subjects)}"
                if weak_subjects else None
            ),
        })

    # --- Lấy một môn cụ thể ---
    subj_key = resolve_subject(subject)
    if subj_key is None:
        return _err(
            "get_grades_by_grade_level",
            f"Môn học '{subject}' không hợp lệ. "
            f"Vui lòng dùng một trong: {', '.join(SUBJECTS)} "
            f"hoặc tương đương tiếng Việt: Toán, Văn, Anh, Lý, Hóa, Sinh, Sử, Địa."
        )

    grades = get_grades(sid, year)
    if grades is None:
        return _err("get_grades_by_grade_level",
                    f"Không có dữ liệu điểm năm {year} cho học sinh '{sid}'.")

    subj_data = grades.get(subj_key, {})
    gpa = subj_data.get("gpa") or compute_gpa(subj_data)

    return _ok("get_grades_by_grade_level", {
        "student_id": sid,
        "name": student["name"],
        "class": student["class"],
        "grade_level": gl,
        "academic_year": year,
        "subject": subj_key,
        "factor_1": subj_data.get("factor_1", []),
        "factor_2": subj_data.get("factor_2", []),
        "factor_3": subj_data.get("factor_3"),
        "gpa": gpa,
        "alert": (
            f"CANH BAO: Diem mon {subj_key} dang duoi trung binh (GPA = {gpa})!"
            if gpa is not None and gpa < 5.0 else None
        ),
    })


# ===========================================================================
# Tool Registry & Specs
# ===========================================================================

# Map tên tool -> hàm Python (dùng trong agent để dispatch)
ACADEMIC_TOOLS = {
    "lookup_student_id": lookup_student_id,
    "get_academic_grades": get_academic_grades,
    "get_conduct_report": get_conduct_report,
    "generate_study_advice": generate_study_advice,
    "verify_parent_phone": verify_parent_phone,
    "search_student_by_name_and_phone": search_student_by_name_and_phone,
    "get_grades_by_grade_level": get_grades_by_grade_level,
}


def get_tool_specs() -> dict:
    """
    Trả về JSON schema mô tả tất cả tool (dùng trong System Prompt của agent).
    """
    return {
        "lookup_student_id": {
            "description": (
                "Tim ma hoc sinh (student_id) theo ten. "
                "Ho tro tim kiem mo (fuzzy matching), khong phan biet dau tieng Viet. "
                "Su dung truoc khi goi cac tool khac neu chua biet student_id."
            ),
            "parameters": {
                "student_name": "string - Ten hoc sinh can tim (co the viet tat hoac thieu dau)"
            },
            "returns": "student_id, ten, lop, so dien thoai phu huynh",
            "example": 'lookup_student_id("Lý Duy Giang")',
        },
        "get_academic_grades": {
            "description": (
                "Lay diem so va GPA cua hoc sinh. "
                "Co the tra cuu mot mon cu the hoac toan bo 8 mon. "
                "Tu dong tinh toan GPA va canh bao hoc luc yeu."
            ),
            "parameters": {
                "student_id": "string - Ma hoc sinh (vd 'S001')",
                "subject": (
                    "string - Ten mon hoc hoac 'All'. "
                    "Mon hop le: Math, Literature, English, Physics, Chemistry, Biology, History, Geography. "
                    "Hoac tieng Viet: Toan, Van, Anh, Ly, Hoa, Sinh, Su, Dia"
                ),
                "academic_year": "string (optional) - Nam hoc vd '2025-2026'. Mac dinh: nam moi nhat",
            },
            "returns": "factor_1, factor_2, factor_3, gpa, canh bao neu GPA < 5.0",
            "example": 'get_academic_grades("S001", "Math")',
        },
        "get_conduct_report": {
            "description": (
                "Lay bao cao chuyen can va hanh kiem cua hoc sinh. "
                "Gom so buoi nghi co phep, khong phep, diem hanh kiem, "
                "xep loai va nhan xet GVCN. "
                "Tu dong canh bao do neu nghi khong phep > 3 buoi."
            ),
            "parameters": {
                "student_id": "string - Ma hoc sinh",
                "academic_year": "string (optional) - Nam hoc. Mac dinh: nam moi nhat",
            },
            "returns": "so buoi nghi, hanh kiem, GPA tong hop, nhan xet GVCN",
            "example": 'get_conduct_report("S001")',
        },
        "generate_study_advice": {
            "description": (
                "Phan tich toan dien va tu van lo trinh cai thien hoc tap. "
                "Dua tren GPA tung mon, xu huong qua cac nam va nhan xet GVCN."
            ),
            "parameters": {
                "student_id": "string - Ma hoc sinh",
            },
            "returns": "xep hang mon yeu/manh, ke hoach cai thien, danh gia tong the",
            "example": 'generate_study_advice("S001")',
        },
        "verify_parent_phone": {
            "description": (
                "Xac thuc so dien thoai phu huynh de lay thong tin hoc sinh. "
                "Co the truyen them grade_level de lay dung lop can tim neu co. "
                "Su dung truoc khi tra loi ve diem so de dam bao bao mat."
            ),
            "parameters": {
                "parent_phone": "string - So dien thoai phu huynh (vd '0901234567')",
                "grade_level": "string (optional) - Lop hoc can tim kiem (vd '10', '11', '12')"
            },
            "returns": "student_id, ten, lop, nam hoc, hoac danh sach cac lop kha dung neu chua chi dinh",
            "example": 'verify_parent_phone("0936538687")',
        },
        "search_student_by_name_and_phone": {
            "description": (
                "Tim hoc sinh chinh xac bang ca ten, so dien thoai phu huynh va grade_level (tuy chon). "
                "Su dung khi can xac dinh chinh xac hoc sinh trong truong hop co nhieu hoc sinh cung ten hoac nhieu nam hoc."
            ),
            "parameters": {
                "name": "string - Ten hoc sinh (fuzzy matching)",
                "parent_phone": "string - So dien thoai phu huynh",
                "grade_level": "string (optional) - Lop hoc can tim kiem (vd '10', '11', '12')"
            },
            "returns": "student_id, ten, lop, grade_level, academic_year, hoặc thông báo nhiều lớp khả dụng",
            "example": 'search_student_by_name_and_phone("Lý Duy Giang", "0990092379", "11")',
        },
        "get_grades_by_grade_level": {
            "description": (
                "Lay diem so cua hoc sinh tai mot lop cu the (grade level nhu 10, 11, 12). "
                "Su dung khi nguoi dung hoi ve diem cua mot lop cu the."
            ),
            "parameters": {
                "student_id": "string - Ma hoc sinh (vd 'S001')",
                "grade_level": "string - Lop can tra cuu (vd '11')",
                "subject": "string - Ten mon hoc hoac 'All' (mac dinh)"
            },
            "returns": "diem cac mon tai lop do, GPA tong hop",
            "example": 'get_grades_by_grade_level("S005", "11")',
        },
    }


# ===========================================================================
# Quick self-test
# ===========================================================================
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=== Tool 1: lookup_student_id ===")
    print(lookup_student_id("Giang"))

    print("\n=== Tool 2: get_academic_grades (Math) ===")
    print(get_academic_grades("S001", "Math"))

    print("\n=== Tool 2: get_academic_grades (All) ===")
    result = json.loads(get_academic_grades("S001", "All"))
    print(f"Overall GPA: {result.get('overall_gpa')}, Weak: {result.get('weak_subjects')}")

    print("\n=== Tool 3: get_conduct_report ===")
    print(get_conduct_report("S006"))  # S006 co nhieu buoi nghi

    print("\n=== Tool 4: generate_study_advice ===")
    result = json.loads(generate_study_advice("S006"))
    print(f"Assessment: {result.get('overall_assessment')}")
    print(f"Weakest: {result.get('weakest_subjects')}")
