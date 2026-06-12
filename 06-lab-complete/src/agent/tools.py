"""
Tools for ReAct agent to search and retrieve student point information.
"""

import csv
import os
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


# Path to student data CSV
CSV_PATH = Path(__file__).parent.parent.parent / "data" / "students.csv"


def load_students() -> List[Dict[str, Any]]:
    """Load student data from CSV file.
    
    Returns:
        List of dictionaries containing student records
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Student data CSV not found at {CSV_PATH}")
    
    students = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert points to int if available, keep None otherwise
            if row['points'].strip():
                row['points'] = int(row['points'])
            else:
                row['points'] = None
            students.append(row)
    return students


def search_student(name: str) -> Dict[str, Any]:
    """Search for student(s) by name (case-insensitive partial match).
    
    Args:
        name: Student name to search for
    
    Returns:
        Dict with status, matching students, and metadata
    """
    timestamp = datetime.now().isoformat()
    
    try:
        students = load_students()
        name_lower = name.lower().strip()
        matches = [
            s for s in students
            if name_lower in s['name'].lower()
        ]
        
        if not matches:
            return {
                "status": "success",
                "found": False,
                "message": f"No students found matching '{name}'",
                "matches": [],
                "timestamp": timestamp,
                "tool": "search_student"
            }
        
        # Format results without sensitive data
        results = [
            {
                "student_id": m['student_id'],
                "name": m['name'],
                "points": m['points'],
                "subject": m['subject'],
                "date_updated": m['date_updated']
            }
            for m in matches
        ]
        
        return {
            "status": "success",
            "found": True,
            "message": f"Found {len(matches)} student(s) matching '{name}'",
            "matches": results,
            "count": len(matches),
            "timestamp": timestamp,
            "tool": "search_student"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error searching for student: {str(e)}",
            "matches": [],
            "timestamp": timestamp,
            "tool": "search_student"
        }


def get_student_points(student_id: str) -> Dict[str, Any]:
    """Get exact points for a specific student by ID.
    
    Args:
        student_id: Student ID to look up
    
    Returns:
        Dict with status, student points, and metadata
    """
    timestamp = datetime.now().isoformat()
    
    try:
        students = load_students()
        student_id_upper = student_id.upper().strip()
        
        matching = [s for s in students if s['student_id'].upper() == student_id_upper]
        
        if not matching:
            return {
                "status": "success",
                "found": False,
                "message": f"No student found with ID '{student_id}'",
                "student": None,
                "timestamp": timestamp,
                "tool": "get_student_points"
            }
        
        student = matching[0]
        
        if student['points'] is None:
            return {
                "status": "success",
                "found": True,
                "message": f"Student {student['name']} (ID: {student_id}) has no recorded points",
                "student": {
                    "student_id": student['student_id'],
                    "name": student['name'],
                    "points": None,
                    "subject": student['subject'],
                    "date_updated": student['date_updated']
                },
                "points": None,
                "timestamp": timestamp,
                "tool": "get_student_points"
            }
        
        return {
            "status": "success",
            "found": True,
            "message": f"Retrieved points for {student['name']}",
            "student": {
                "student_id": student['student_id'],
                "name": student['name'],
                "points": student['points'],
                "subject": student['subject'],
                "date_updated": student['date_updated']
            },
            "points": student['points'],
            "timestamp": timestamp,
            "tool": "get_student_points"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving student points: {str(e)}",
            "student": None,
            "timestamp": timestamp,
            "tool": "get_student_points"
        }


# Tool registry for dynamic dispatch
TOOLS = {
    "search_student": search_student,
    "get_student_points": get_student_points
}


def get_tool_specs() -> Dict[str, Dict[str, Any]]:
    """Get JSON schema specifications for all available tools.
    
    Returns:
        Dictionary mapping tool names to their specifications
    """
    return {
        "search_student": {
            "description": "Search for student(s) by name (case-insensitive partial match). Returns all students whose names contain the search term.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The student's name to search for (partial matches allowed)"
                    }
                },
                "required": ["name"]
            }
        },
        "get_student_points": {
            "description": "Get the exact points for a student by their student ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "The unique student ID (e.g., 'S001')"
                    }
                },
                "required": ["student_id"]
            }
        }
    }


if __name__ == "__main__":
    # Test the tools
    print("Testing search_student:")
    result = search_student("John")
    print(json.dumps(result, indent=2))
    
    print("\nTesting get_student_points:")
    result = get_student_points("S001")
    print(json.dumps(result, indent=2))
    
    print("\nTesting get_student_points (invalid ID):")
    result = get_student_points("S999")
    print(json.dumps(result, indent=2))
