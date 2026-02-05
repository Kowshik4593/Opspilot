"""
Comprehensive Quality Tests for AWOA Application
=================================================
This test suite performs detailed quality analysis of all endpoints and features,
using Azure OpenAI LLM for intelligent validation of response quality.

Run with: python tests/comprehensive_quality_tests.py
"""

import sys
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import traceback

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import SETTINGS

# Azure OpenAI configuration
try:
    from openai import AzureOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: OpenAI library not installed. Install with: pip install openai")

# Test configuration
API_BASE = "http://localhost:8002/api/v1"
FRONTEND_BASE = "http://localhost:3000"
# Match the actual user in the data repository
TEST_USER_EMAIL = "kowshik.naidu@contoso.com"

@dataclass
class TestResult:
    """Individual test result with quality metrics"""
    test_name: str
    category: str
    passed: bool
    quality_score: float  # 0-100
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    quality_analysis: str = ""
    recommendations: List[str] = field(default_factory=list)

@dataclass
class TestReport:
    """Complete test report"""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_quality_score: float
    avg_response_time_ms: float
    results: List[TestResult] = field(default_factory=list)
    summary: str = ""
    critical_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class QualityAnalyzer:
    """Uses Azure OpenAI to analyze response quality"""
    
    def __init__(self):
        self.client = None
        if HAS_OPENAI and SETTINGS["models"]["azure_api_key"]:
            try:
                self.client = AzureOpenAI(
                    api_key=SETTINGS["models"]["azure_api_key"],
                    api_version="2024-02-15-preview",
                    azure_endpoint=SETTINGS["models"]["azure_api_base"]
                )
                self.model = SETTINGS["models"]["chat_model"]
                print(f"✓ Azure OpenAI initialized with model: {self.model}")
            except Exception as e:
                print(f"✗ Failed to initialize Azure OpenAI: {e}")
                self.client = None
    
    def analyze_response(self, endpoint: str, request_data: Any, response_data: Any, 
                         expected_criteria: List[str]) -> Dict[str, Any]:
        """Analyze response quality using LLM"""
        if not self.client:
            return self._fallback_analysis(response_data, expected_criteria)
        
        try:
            prompt = f"""Analyze the quality of this API response.

Endpoint: {endpoint}
Request: {json.dumps(request_data, indent=2) if request_data else 'N/A'}
Response: {json.dumps(response_data, indent=2) if isinstance(response_data, (dict, list)) else str(response_data)[:2000]}

Expected criteria for quality:
{chr(10).join(f'- {c}' for c in expected_criteria)}

Provide your analysis in this JSON format:
{{
    "quality_score": <0-100>,
    "passed": <true/false>,
    "issues": ["issue1", "issue2"],
    "strengths": ["strength1", "strength2"],
    "recommendations": ["rec1", "rec2"],
    "detailed_analysis": "Your detailed analysis here"
}}

Be strict but fair. Score based on:
- Data completeness and correctness
- Proper formatting and structure
- Meaningful content (not empty/null values)
- Adherence to expected criteria
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a quality assurance expert analyzing API responses. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            return json.loads(result_text)
        except Exception as e:
            print(f"  LLM analysis error: {e}")
            return self._fallback_analysis(response_data, expected_criteria)
    
    def _fallback_analysis(self, response_data: Any, expected_criteria: List[str]) -> Dict[str, Any]:
        """Fallback analysis when LLM is not available"""
        issues = []
        strengths = []
        score = 50  # Base score
        
        if response_data is None:
            return {
                "quality_score": 0,
                "passed": False,
                "issues": ["Response is null/None"],
                "strengths": [],
                "recommendations": ["Check if endpoint returns data"],
                "detailed_analysis": "No response data received"
            }
        
        if isinstance(response_data, list):
            if len(response_data) > 0:
                score += 20
                strengths.append(f"Returns {len(response_data)} items")
            else:
                score -= 10
                issues.append("Empty list returned")
        
        if isinstance(response_data, dict):
            if len(response_data) > 0:
                score += 20
                strengths.append(f"Contains {len(response_data)} fields")
                # Check for null values
                nulls = [k for k, v in response_data.items() if v is None]
                if nulls:
                    issues.append(f"Null values in: {nulls}")
                    score -= 5 * len(nulls)
            else:
                issues.append("Empty object returned")
        
        # Check expected criteria
        for criterion in expected_criteria:
            if "required" in criterion.lower():
                score += 5
        
        return {
            "quality_score": max(0, min(100, score)),
            "passed": score >= 50,
            "issues": issues,
            "strengths": strengths,
            "recommendations": ["Enable LLM analysis for detailed quality assessment"],
            "detailed_analysis": "Basic structural analysis performed"
        }

class ComprehensiveQualityTester:
    """Main test orchestrator"""
    
    def __init__(self):
        self.analyzer = QualityAnalyzer()
        self.results: List[TestResult] = []
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, url: str, data: Any = None, 
                           headers: Dict = None) -> tuple:
        """Make HTTP request and measure response time"""
        start_time = datetime.now()
        try:
            headers = headers or {"Content-Type": "application/json"}
            if method == "GET":
                async with self.session.get(url, headers=headers) as resp:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    if resp.content_type == "application/json":
                        return await resp.json(), resp.status, response_time
                    return await resp.text(), resp.status, response_time
            elif method == "POST":
                async with self.session.post(url, json=data, headers=headers) as resp:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    if resp.content_type == "application/json":
                        return await resp.json(), resp.status, response_time
                    return await resp.text(), resp.status, response_time
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return None, 0, response_time
    
    def add_result(self, result: TestResult):
        """Add test result"""
        self.results.append(result)
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status} [{result.quality_score:.0f}/100] {result.test_name} ({result.response_time_ms:.0f}ms)")
        if result.errors:
            for error in result.errors:
                print(f"    Error: {error}")
    
    # =====================================================================
    # EMAIL TESTS
    # =====================================================================
    
    async def test_emails_list(self):
        """Test GET /emails - Quality check on email list"""
        print("\n📧 Testing Email Endpoints...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/emails")
        
        criteria = [
            "Returns array of email objects",
            "Each email has required fields: email_id, subject, from_email, body_text",
            "Emails have proper timestamps (received_utc)",
            "Actionability classification is present (actionable/informational/noise)",
            "Sender information is complete"
        ]
        
        analysis = self.analyzer.analyze_response("/emails", None, data, criteria)
        
        # Additional structural checks
        errors = []
        if status != 200:
            errors.append(f"Expected status 200, got {status}")
        if not isinstance(data, list):
            errors.append("Response is not a list")
        elif len(data) == 0:
            errors.append("No emails returned")
        else:
            # Check first email structure
            required_fields = ["email_id", "subject", "from_email", "body_text"]
            sample = data[0]
            missing = [f for f in required_fields if f not in sample or not sample[f]]
            if missing:
                errors.append(f"Missing required fields in email: {missing}")
        
        self.add_result(TestResult(
            test_name="GET /emails - List all emails",
            category="Emails",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details={"count": len(data) if isinstance(data, list) else 0},
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_emails_filter_actionable(self):
        """Test email filtering by actionable category"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/emails?category=actionable")
        
        criteria = [
            "Only returns actionable emails",
            "Each email has actionability_gt = 'actionable'",
            "Actionable emails have clear action requirements"
        ]
        
        analysis = self.analyzer.analyze_response("/emails?category=actionable", None, data, criteria)
        
        errors = []
        if isinstance(data, list) and len(data) > 0:
            non_actionable = [e for e in data if e.get("actionability_gt") != "actionable"]
            if non_actionable:
                errors.append(f"{len(non_actionable)} emails don't have actionability_gt='actionable'")
        
        self.add_result(TestResult(
            test_name="GET /emails?category=actionable - Filter actionable",
            category="Emails",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details={"filtered_count": len(data) if isinstance(data, list) else 0},
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_email_analysis(self):
        """Test AI email analysis endpoint"""
        # First get an email to analyze
        emails_data, _, _ = await self.make_request("GET", f"{API_BASE}/emails")
        
        if not emails_data or not isinstance(emails_data, list) or len(emails_data) == 0:
            self.add_result(TestResult(
                test_name="POST /ai/email/analyze - AI Email Analysis",
                category="AI/Emails",
                passed=False,
                quality_score=0,
                response_time_ms=0,
                errors=["No emails available to analyze"],
                recommendations=["Ensure email data is loaded"]
            ))
            return
        
        email_id = emails_data[0]["email_id"]
        request_data = {"email_id": email_id, "user_email": TEST_USER_EMAIL}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/email/analyze", request_data)
        
        criteria = [
            "Returns comprehensive email analysis",
            "Includes triage/classification result",
            "Provides summary of email content",
            "Suggests appropriate actions",
            "May include draft reply if actionable",
            "Analysis is accurate to email content"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/email/analyze", request_data, data, criteria)
        
        errors = []
        if status not in [200, 500]:
            errors.append(f"Unexpected status: {status}")
        
        self.add_result(TestResult(
            test_name="POST /ai/email/analyze - AI Email Analysis",
            category="AI/Emails",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details={"email_id": email_id},
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # TASKS TESTS
    # =====================================================================
    
    async def test_tasks_list(self):
        """Test GET /tasks - Quality check on task list"""
        print("\n✅ Testing Task Endpoints...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/tasks")
        
        criteria = [
            "Returns array of task objects",
            "Each task has: task_id, title, description, priority, status",
            "Priority values are valid (P0-P3)",
            "Status values are valid (todo/in_progress/completed/blocked)",
            "Due dates are properly formatted ISO timestamps",
            "Tasks have meaningful titles and descriptions"
        ]
        
        analysis = self.analyzer.analyze_response("/tasks", None, data, criteria)
        
        errors = []
        if not isinstance(data, list):
            errors.append("Response is not a list")
        elif len(data) > 0:
            # Validate priorities
            valid_priorities = ["P0", "P1", "P2", "P3"]
            invalid_priorities = [t.get("priority") for t in data if t.get("priority") not in valid_priorities]
            if invalid_priorities:
                errors.append(f"Invalid priorities found: {set(invalid_priorities)}")
            
            # Validate statuses
            valid_statuses = ["todo", "in_progress", "completed", "blocked", "scheduled", "done"]
            invalid_statuses = [t.get("status") for t in data if t.get("status") not in valid_statuses]
            if invalid_statuses:
                errors.append(f"Invalid statuses found: {set(invalid_statuses)}")
            
            # Check for P0 tasks (critical)
            p0_tasks = [t for t in data if t.get("priority") == "P0"]
            analysis["details"] = {"total": len(data), "p0_count": len(p0_tasks)}
        
        self.add_result(TestResult(
            test_name="GET /tasks - List all tasks",
            category="Tasks",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details=analysis.get("details", {}),
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_day_plan(self):
        """Test AI day planning endpoint"""
        request_data = {"user_email": TEST_USER_EMAIL}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/plan_today", request_data)
        
        criteria = [
            "Returns a structured day plan",
            "Prioritizes P0 and urgent tasks first",
            "Considers meeting schedule",
            "Provides time blocks for focus work",
            "Includes realistic time estimates",
            "Suggests breaks and wellness checks"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/plan_today", request_data, data, criteria)
        
        self.add_result(TestResult(
            test_name="POST /ai/plan_today - AI Day Planning",
            category="AI/Tasks",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # MEETINGS TESTS
    # =====================================================================
    
    async def test_meetings_list(self):
        """Test GET /meetings - Quality check on meetings"""
        print("\n📅 Testing Meeting Endpoints...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/meetings")
        
        criteria = [
            "Returns array of meeting objects",
            "Each meeting has: meeting_id, title, scheduled_start_utc, scheduled_end_utc",
            "Meeting times are valid ISO timestamps",
            "Participant information is present",
            "Meeting type/category is specified",
            "Location or virtual meeting link is provided"
        ]
        
        analysis = self.analyzer.analyze_response("/meetings", None, data, criteria)
        
        errors = []
        if isinstance(data, list) and len(data) > 0:
            # Check for required fields
            sample = data[0]
            required = ["meeting_id", "title"]
            missing = [f for f in required if f not in sample]
            if missing:
                errors.append(f"Missing required fields: {missing}")
            
            # Check time fields
            time_fields = ["scheduled_start_utc", "scheduled_end_utc", "start_utc", "end_utc"]
            has_time = any(f in sample for f in time_fields)
            if not has_time:
                errors.append("No time fields found in meeting")
        
        self.add_result(TestResult(
            test_name="GET /meetings - List all meetings",
            category="Meetings",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details={"count": len(data) if isinstance(data, list) else 0},
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_meeting_mom(self):
        """Test meeting MoM (Minutes of Meeting) endpoint"""
        # First get meetings
        meetings_data, _, _ = await self.make_request("GET", f"{API_BASE}/meetings")
        
        if not meetings_data or len(meetings_data) == 0:
            self.add_result(TestResult(
                test_name="GET /meetings/{id}/mom - Meeting Minutes",
                category="Meetings",
                passed=False,
                quality_score=0,
                response_time_ms=0,
                errors=["No meetings available"]
            ))
            return
        
        meeting_id = meetings_data[0]["meeting_id"]
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/meetings/{meeting_id}/mom")
        
        criteria = [
            "Returns meeting minutes/summary",
            "Includes key decisions made",
            "Lists action items with owners",
            "Captures attendees",
            "Provides meeting summary",
            "Action items have due dates"
        ]
        
        analysis = self.analyzer.analyze_response(f"/meetings/{meeting_id}/mom", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /meetings/{id}/mom - Meeting Minutes",
            category="Meetings",
            passed=analysis["passed"] if data else False,
            quality_score=analysis["quality_score"] if data else 0,
            response_time_ms=resp_time,
            details={"meeting_id": meeting_id, "has_mom": data is not None},
            errors=analysis.get("issues", []) if data else ["No MoM available for this meeting"],
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_generate_mom(self):
        """Test AI MoM generation"""
        meetings_data, _, _ = await self.make_request("GET", f"{API_BASE}/meetings")
        
        if not meetings_data or len(meetings_data) == 0:
            self.add_result(TestResult(
                test_name="POST /ai/meeting/mom - Generate AI MoM",
                category="AI/Meetings",
                passed=False,
                quality_score=0,
                response_time_ms=0,
                errors=["No meetings available"]
            ))
            return
        
        meeting_id = meetings_data[0]["meeting_id"]
        request_data = {"meeting_id": meeting_id}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/meeting/mom", request_data)
        
        criteria = [
            "Generates coherent meeting summary",
            "Extracts key decisions accurately",
            "Identifies action items with owners",
            "Captures important discussion points",
            "Uses professional language",
            "Is structured and easy to read"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/meeting/mom", request_data, data, criteria)
        
        self.add_result(TestResult(
            test_name="POST /ai/meeting/mom - Generate AI MoM",
            category="AI/Meetings",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details={"meeting_id": meeting_id},
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # FOLLOWUPS/NUDGES TESTS
    # =====================================================================
    
    async def test_followups_list(self):
        """Test GET /followups - Quality check on follow-ups"""
        print("\n🔔 Testing Follow-up/Nudge Endpoints...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/followups")
        
        criteria = [
            "Returns array of follow-up items",
            "Each followup has: followup_id, reason, severity, due date",
            "Severity levels are valid (critical/high/medium/low)",
            "Draft messages are provided for actionable follow-ups",
            "Recommended channel is specified (email/slack/teams)",
            "Due dates are realistic and properly formatted"
        ]
        
        analysis = self.analyzer.analyze_response("/followups", None, data, criteria)
        
        errors = []
        if isinstance(data, list) and len(data) > 0:
            valid_severities = ["critical", "high", "medium", "low"]
            invalid = [f.get("severity") for f in data if f.get("severity") not in valid_severities]
            if invalid:
                errors.append(f"Invalid severities found: {set(invalid)}")
            
            # Check for critical items
            critical = [f for f in data if f.get("severity") == "critical"]
            if critical:
                analysis["details"] = {"total": len(data), "critical": len(critical)}
        
        self.add_result(TestResult(
            test_name="GET /followups - List follow-ups",
            category="Followups",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details=analysis.get("details", {}),
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_nudges(self):
        """Test AI nudges endpoint"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/nudges")
        
        criteria = [
            "Returns proactive nudge/reminder list",
            "Nudges are contextually relevant",
            "Priority order makes sense",
            "Clear action suggestions provided",
            "Appropriate timing for nudges"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/nudges", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/nudges - AI Nudges",
            category="AI/Nudges",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # WELLNESS TESTS
    # =====================================================================
    
    async def test_wellness_config(self):
        """Test GET /wellness - Wellness configuration"""
        print("\n💚 Testing Wellness Endpoints...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/wellness")
        
        criteria = [
            "Returns wellness configuration",
            "Includes score/metrics",
            "Has threshold definitions",
            "Configures proactive nudges",
            "Defines focus block settings"
        ]
        
        analysis = self.analyzer.analyze_response("/wellness", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /wellness - Wellness Config",
            category="Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_wellness_score(self):
        """Test AI wellness score calculation"""
        request_data = {"user_email": TEST_USER_EMAIL}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/wellness/score", request_data)
        
        criteria = [
            "Returns calculated wellness score (0-100)",
            "Score is based on multiple factors",
            "Provides breakdown of contributing factors",
            "Includes actionable recommendations",
            "Score level classification (healthy/moderate/elevated/critical)"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/score", request_data, data, criteria)
        
        errors = []
        if isinstance(data, dict):
            score = data.get("score") or data.get("wellness_score")
            if score is not None and (score < 0 or score > 100):
                errors.append(f"Score {score} is out of range (0-100)")
        
        self.add_result(TestResult(
            test_name="POST /ai/wellness/score - Calculate Wellness",
            category="AI/Wellness",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_wellness_joke(self):
        """Test wellness joke endpoint"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/wellness/joke")
        
        criteria = [
            "Returns a joke or humorous content",
            "Content is work-appropriate",
            "Joke is actually funny/amusing",
            "Not offensive or inappropriate"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/joke", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/wellness/joke - Wellness Joke",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_wellness_motivation(self):
        """Test motivational content endpoint"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/wellness/motivate")
        
        criteria = [
            "Returns motivational quote or message",
            "Content is inspiring and positive",
            "Appropriate for work context",
            "Includes attribution if quote"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/motivate", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/wellness/motivate - Motivation",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_wellness_break(self):
        """Test break suggestion endpoint"""
        request_data = {"break_type": "short"}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/wellness/break", request_data)
        
        criteria = [
            "Returns break activity suggestion",
            "Suggestion matches requested break type",
            "Includes duration estimate",
            "Activity is practical and doable",
            "Benefits/purpose explained"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/break", request_data, data, criteria)
        
        self.add_result(TestResult(
            test_name="POST /ai/wellness/break - Break Suggestion",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_wellness_breathing(self):
        """Test breathing exercise endpoint"""
        request_data = {"exercise_type": "box"}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/wellness/breathing", request_data)
        
        criteria = [
            "Returns breathing exercise instructions",
            "Includes clear step-by-step guide",
            "Timing is specified (seconds per phase)",
            "Exercise type matches request",
            "Benefits are explained"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/breathing", request_data, data, criteria)
        
        self.add_result(TestResult(
            test_name="POST /ai/wellness/breathing - Breathing Exercise",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_wellness_mood_logging(self):
        """Test mood logging endpoint"""
        request_data = {"mood": "good", "user_email": TEST_USER_EMAIL}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/wellness/mood", request_data)
        
        criteria = [
            "Successfully logs mood entry",
            "Returns confirmation",
            "May include personalized response",
            "Suggests relevant activities based on mood"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/mood", request_data, data, criteria)
        
        self.add_result(TestResult(
            test_name="POST /ai/wellness/mood - Log Mood",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_burnout_risk(self):
        """Test burnout risk assessment"""
        request_data = {"user_email": TEST_USER_EMAIL}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/ai/wellness/burnout", request_data)
        
        criteria = [
            "Returns burnout risk assessment",
            "Risk level is clearly indicated",
            "Contributing factors identified",
            "Actionable recommendations provided",
            "Assessment is data-driven"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/burnout", request_data, data, criteria)
        
        self.add_result(TestResult(
            test_name="POST /ai/wellness/burnout - Burnout Risk",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_focus_blocks(self):
        """Test focus block suggestions"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/wellness/focus_blocks")
        
        criteria = [
            "Returns suggested focus time blocks",
            "Blocks don't conflict with meetings",
            "Duration is reasonable (25-120 mins)",
            "Tasks are assigned to blocks",
            "Respects typical work hours"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/focus_blocks", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/wellness/focus_blocks - Focus Blocks",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_meeting_detox(self):
        """Test meeting detox suggestions"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/wellness/meeting_detox")
        
        criteria = [
            "Returns meeting optimization suggestions",
            "Identifies meetings that could be emails",
            "Suggests meeting consolidation",
            "Recommends meeting-free blocks",
            "Actionable and specific suggestions"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/wellness/meeting_detox", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/wellness/meeting_detox - Meeting Detox",
            category="AI/Wellness",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # REPORTS TESTS
    # =====================================================================
    
    async def test_eod_report(self):
        """Test EOD report generation"""
        print("\n📊 Testing Report Endpoints...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/reports/eod")
        
        criteria = [
            "Returns end-of-day report",
            "Lists completed tasks",
            "Shows pending/incomplete tasks",
            "Includes blockers if any",
            "Highlights key achievements",
            "Meeting summary included"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/reports/eod", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/reports/eod - EOD Report",
            category="Reports",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    async def test_weekly_report(self):
        """Test weekly report generation"""
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/ai/reports/weekly")
        
        criteria = [
            "Returns weekly summary report",
            "Covers full week period",
            "Shows total tasks completed",
            "Includes meeting statistics",
            "Wellness trend over the week",
            "Highlights and achievements listed"
        ]
        
        analysis = self.analyzer.analyze_response("/ai/reports/weekly", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /ai/reports/weekly - Weekly Report",
            category="Reports",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # ASSISTANT/CHAT TESTS
    # =====================================================================
    
    async def test_assistant_start(self):
        """Test assistant chat start"""
        print("\n🤖 Testing Assistant/Chat Endpoints...")
        
        request_data = {"user_email": TEST_USER_EMAIL}
        data, status, resp_time = await self.make_request("POST", f"{API_BASE}/assistant/start", request_data)
        
        criteria = [
            "Returns session ID",
            "Session is properly initialized",
            "Quick response time"
        ]
        
        analysis = self.analyzer.analyze_response("/assistant/start", request_data, data, criteria)
        
        errors = []
        session_id = None
        if isinstance(data, dict):
            session_id = data.get("session_id")
            if not session_id:
                errors.append("No session_id returned")
        
        self.add_result(TestResult(
            test_name="POST /assistant/start - Start Chat Session",
            category="Assistant",
            passed=analysis["passed"] and not errors,
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            details={"session_id": session_id},
            errors=errors + analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
        
        return session_id
    
    async def test_assistant_chat_queries(self):
        """Test various assistant chat queries"""
        # Start session first
        start_data, _, _ = await self.make_request("POST", f"{API_BASE}/assistant/start", {"user_email": TEST_USER_EMAIL})
        session_id = start_data.get("session_id") if isinstance(start_data, dict) else None
        
        test_queries = [
            {
                "message": "What are my P0 tasks for today?",
                "criteria": [
                    "Lists P0 (highest priority) tasks",
                    "Shows task titles and due dates",
                    "Prioritizes correctly",
                    "Response is helpful and actionable"
                ]
            },
            {
                "message": "Give me my daily brief",
                "criteria": [
                    "Provides comprehensive daily overview",
                    "Includes tasks, meetings, emails summary",
                    "Highlights urgent items",
                    "Shows wellness status",
                    "Actionable recommendations"
                ]
            },
            {
                "message": "Show me actionable emails",
                "criteria": [
                    "Lists emails requiring action",
                    "Shows sender and subject",
                    "Indicates urgency/priority",
                    "Suggests responses if applicable"
                ]
            },
            {
                "message": "What meetings do I have today?",
                "criteria": [
                    "Lists today's meetings",
                    "Shows time and participants",
                    "Indicates meeting type",
                    "Provides preparation suggestions"
                ]
            }
        ]
        
        for query in test_queries:
            request_data = {
                "session_id": session_id,
                "user_email": TEST_USER_EMAIL,
                "message": query["message"]
            }
            data, status, resp_time = await self.make_request("POST", f"{API_BASE}/assistant/chat", request_data)
            
            analysis = self.analyzer.analyze_response("/assistant/chat", request_data, data, query["criteria"])
            
            errors = []
            if isinstance(data, dict):
                response_text = data.get("response", "")
                if not response_text or len(response_text) < 10:
                    errors.append("Response is empty or too short")
            
            self.add_result(TestResult(
                test_name=f"Assistant Query: '{query['message'][:30]}...'",
                category="Assistant",
                passed=analysis["passed"] and not errors,
                quality_score=analysis["quality_score"],
                response_time_ms=resp_time,
                details={"query": query["message"]},
                errors=errors + analysis.get("issues", []),
                quality_analysis=analysis.get("detailed_analysis", ""),
                recommendations=analysis.get("recommendations", [])
            ))
    
    # =====================================================================
    # AUTONOMOUS AGENT TESTS
    # =====================================================================
    
    async def test_autonomous_status(self):
        """Test autonomous agent status"""
        print("\n🤖 Testing Autonomous Agent...")
        
        data, status, resp_time = await self.make_request("GET", f"{API_BASE}/autonomous/status")
        
        criteria = [
            "Returns agent status (running/stopped)",
            "Includes relevant state information",
            "Quick response"
        ]
        
        analysis = self.analyzer.analyze_response("/autonomous/status", None, data, criteria)
        
        self.add_result(TestResult(
            test_name="GET /autonomous/status - Agent Status",
            category="Autonomous",
            passed=analysis["passed"],
            quality_score=analysis["quality_score"],
            response_time_ms=resp_time,
            errors=analysis.get("issues", []),
            quality_analysis=analysis.get("detailed_analysis", ""),
            recommendations=analysis.get("recommendations", [])
        ))
    
    # =====================================================================
    # HEALTH CHECK
    # =====================================================================
    
    async def test_health_check(self):
        """Test API health endpoint"""
        print("\n🏥 Testing Health Check...")
        
        data, status, resp_time = await self.make_request("GET", "http://localhost:8002/health")
        
        errors = []
        quality_score = 100
        
        if status != 200:
            errors.append(f"Health check returned status {status}")
            quality_score = 0
        
        if isinstance(data, dict) and data.get("status") != "ok":
            errors.append(f"Health status is not 'ok': {data}")
            quality_score = 50
        
        self.add_result(TestResult(
            test_name="GET /health - API Health Check",
            category="System",
            passed=not errors,
            quality_score=quality_score,
            response_time_ms=resp_time,
            errors=errors
        ))
    
    # =====================================================================
    # GENERATE REPORT
    # =====================================================================
    
    def generate_report(self) -> TestReport:
        """Generate comprehensive test report"""
        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]
        
        avg_quality = sum(r.quality_score for r in self.results) / len(self.results) if self.results else 0
        avg_response = sum(r.response_time_ms for r in self.results) / len(self.results) if self.results else 0
        
        # Identify critical issues
        critical_issues = []
        for r in failed:
            if r.quality_score < 30:
                critical_issues.append(f"{r.test_name}: {', '.join(r.errors[:2])}")
        
        # Collect recommendations
        all_recommendations = []
        for r in self.results:
            all_recommendations.extend(r.recommendations)
        unique_recommendations = list(set(all_recommendations))[:10]
        
        report = TestReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed_tests=len(passed),
            failed_tests=len(failed),
            avg_quality_score=avg_quality,
            avg_response_time_ms=avg_response,
            results=self.results,
            critical_issues=critical_issues,
            recommendations=unique_recommendations
        )
        
        return report
    
    # =====================================================================
    # RUN ALL TESTS
    # =====================================================================
    
    async def run_all_tests(self):
        """Run all quality tests"""
        print("=" * 70)
        print("AWOA Comprehensive Quality Test Suite")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Base: {API_BASE}")
        print(f"Test User: {TEST_USER_EMAIL}")
        print("=" * 70)
        
        # Health check first
        await self.test_health_check()
        
        # Email tests
        await self.test_emails_list()
        await self.test_emails_filter_actionable()
        await self.test_email_analysis()
        
        # Task tests
        await self.test_tasks_list()
        await self.test_day_plan()
        
        # Meeting tests
        await self.test_meetings_list()
        await self.test_meeting_mom()
        await self.test_generate_mom()
        
        # Followup tests
        await self.test_followups_list()
        await self.test_nudges()
        
        # Wellness tests
        await self.test_wellness_config()
        await self.test_wellness_score()
        await self.test_wellness_joke()
        await self.test_wellness_motivation()
        await self.test_wellness_break()
        await self.test_wellness_breathing()
        await self.test_wellness_mood_logging()
        await self.test_burnout_risk()
        await self.test_focus_blocks()
        await self.test_meeting_detox()
        
        # Report tests
        await self.test_eod_report()
        await self.test_weekly_report()
        
        # Assistant tests
        await self.test_assistant_start()
        await self.test_assistant_chat_queries()
        
        # Autonomous agent tests
        await self.test_autonomous_status()
        
        # Generate and display report
        report = self.generate_report()
        self.display_report(report)
        
        return report
    
    def display_report(self, report: TestReport):
        """Display formatted test report"""
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        # Overall stats
        pass_rate = (report.passed_tests / report.total_tests * 100) if report.total_tests > 0 else 0
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Tests: {report.total_tests}")
        print(f"   ✓ Passed: {report.passed_tests}")
        print(f"   ✗ Failed: {report.failed_tests}")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        print(f"   Avg Quality Score: {report.avg_quality_score:.1f}/100")
        print(f"   Avg Response Time: {report.avg_response_time_ms:.0f}ms")
        
        # Results by category
        categories = {}
        for r in report.results:
            if r.category not in categories:
                categories[r.category] = {"passed": 0, "failed": 0, "quality": []}
            if r.passed:
                categories[r.category]["passed"] += 1
            else:
                categories[r.category]["failed"] += 1
            categories[r.category]["quality"].append(r.quality_score)
        
        print(f"\n📁 Results by Category:")
        for cat, stats in categories.items():
            avg_q = sum(stats["quality"]) / len(stats["quality"]) if stats["quality"] else 0
            total = stats["passed"] + stats["failed"]
            print(f"   {cat}: {stats['passed']}/{total} passed (Avg Quality: {avg_q:.0f}/100)")
        
        # Critical issues
        if report.critical_issues:
            print(f"\n🚨 Critical Issues ({len(report.critical_issues)}):")
            for issue in report.critical_issues[:5]:
                print(f"   • {issue}")
        
        # Failed tests details
        failed = [r for r in report.results if not r.passed]
        if failed:
            print(f"\n❌ Failed Tests Details:")
            for r in failed[:10]:
                print(f"\n   [{r.quality_score:.0f}/100] {r.test_name}")
                if r.errors:
                    for e in r.errors[:3]:
                        print(f"      ↳ {e}")
                if r.quality_analysis:
                    print(f"      Analysis: {r.quality_analysis[:150]}...")
        
        # Top recommendations
        if report.recommendations:
            print(f"\n💡 Top Recommendations:")
            for rec in report.recommendations[:5]:
                print(f"   • {rec}")
        
        # Quality analysis summary
        high_quality = [r for r in report.results if r.quality_score >= 80]
        medium_quality = [r for r in report.results if 50 <= r.quality_score < 80]
        low_quality = [r for r in report.results if r.quality_score < 50]
        
        print(f"\n🎯 Quality Distribution:")
        print(f"   High Quality (80-100): {len(high_quality)} tests")
        print(f"   Medium Quality (50-79): {len(medium_quality)} tests")
        print(f"   Low Quality (0-49): {len(low_quality)} tests")
        
        # Performance analysis
        slow_tests = [r for r in report.results if r.response_time_ms > 5000]
        if slow_tests:
            print(f"\n⏱️ Slow Endpoints (>5s):")
            for r in slow_tests:
                print(f"   • {r.test_name}: {r.response_time_ms:.0f}ms")
        
        print("\n" + "=" * 70)
        print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)


async def main():
    """Main entry point"""
    async with ComprehensiveQualityTester() as tester:
        report = await tester.run_all_tests()
        
        # Save report to file
        report_path = ROOT / "tests" / "quality_test_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert report to dict for JSON serialization
        report_dict = {
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "avg_quality_score": report.avg_quality_score,
            "avg_response_time_ms": report.avg_response_time_ms,
            "critical_issues": report.critical_issues,
            "recommendations": report.recommendations,
            "results": [
                {
                    "test_name": r.test_name,
                    "category": r.category,
                    "passed": r.passed,
                    "quality_score": r.quality_score,
                    "response_time_ms": r.response_time_ms,
                    "details": r.details,
                    "errors": r.errors,
                    "quality_analysis": r.quality_analysis,
                    "recommendations": r.recommendations
                }
                for r in report.results
            ]
        }
        
        report_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
        print(f"\n📄 Full report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
