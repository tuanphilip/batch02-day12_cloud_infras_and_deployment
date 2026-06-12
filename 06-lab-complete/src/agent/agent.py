import os
import re
import json
import time
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.agent.academic_tools import ACADEMIC_TOOLS as TOOLS, get_tool_specs

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Generate system prompt with tool specifications and ReAct format instructions.
        Includes available tools, their descriptions, and strict format rules.
        """
        tool_specs = get_tool_specs()
        
        tools_section = "## Available Tools:\n\n"
        for tool_name, spec in tool_specs.items():
            tools_section += f"### {tool_name}\n"
            tools_section += f"**Description:** {spec['description']}\n"
            tools_section += f"**Parameters:** {json.dumps(spec['parameters'], indent=2)}\n\n"
        
        return f"""You are a helpful assistant with access to tools for retrieving student point information.

{tools_section}

## Instructions:

1. Follow the Thought-Action-Observation format strictly.
2. For each step, first explain your reasoning (Thought).
3. Then call exactly ONE tool using the format: Action: tool_name(param_name=value)
4. Wait for the Observation (tool result).
5. Repeat until you have enough information to answer the user's question.
6. When you have the answer, state: Final Answer: [your response]

## Format Rules:

- Thought: (your reasoning about what to do next)
- Action: (tool call in format: tool_name(param_name=value))
- Observation: (you will receive the tool result)
- ... (repeat as needed)
- Final Answer: (your final response to the user)

## SMART RULES:

1. **Verification & Accuracy Rule**:
   - You MUST verify the parent's phone number before sharing grade information.
   - If a search or verification tool returns `"multiple_grades": true` (meaning the student has grade data in grade 10, 11, and 12) and the user has NOT specified which grade level they want in their query, you MUST ask the user: "Tìm thấy điểm của học sinh X ở các lớp: lớp 10, lớp 11, lớp 12. Bạn muốn tìm điểm của học sinh X lớp mấy?" in your Final Answer. Do not guess the grade.
   - If the user specifies the grade level (e.g. "lớp 11"), use `get_grades_by_grade_level` or pass `grade_level` to `search_student_by_name_and_phone` or `verify_parent_phone` to fetch the EXACT row.

2. **Premium Natural Language Output Rule**:
   - Your final answer MUST present the student's grades in a polite, detailed, and beautifully structured Vietnamese natural language format.
   - Do NOT output raw JSON or basic bullet points. Format the output with bold headings, detailing each subject's factor 1, factor 2, factor 3 scores and GPA, along with the overall GPA, conduct grade, behavior score, and the teacher's remarks in a warm parent-friendly tone.

IMPORTANT:
- Call only ONE tool per step
- Use exact parameter names from the tool specifications
- If a tool returns an error, try a different approach or tool
- Always end with Final Answer when you have the information needed"""

    def run(self, user_input: str) -> str:
        """
        Execute the ReAct loop: Thought -> Action -> Observation -> repeat until Final Answer.
        
        Args:
            user_input: The user's question/query
        
        Returns:
            The final answer from the agent
        """
        start_time = time.time()
        
        # Log agent start
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "provider": self.llm.__class__.__name__,
            "max_steps": self.max_steps
        })
        
        # Initialize conversation history
        self.history = []
        steps = 0
        final_answer = None
        total_tokens = {"prompt": 0, "completion": 0}
        
        while steps < self.max_steps:
            # Build prompt for this step
            prompt_text = self._build_prompt(user_input)
            
            # Call LLM
            try:
                response = self.llm.generate(
                    prompt=prompt_text,
                    system_prompt=self.get_system_prompt()
                )
                llm_output = response.get("content", "")
                
                # Track tokens
                usage = response.get("usage", {})
                total_tokens["prompt"] += usage.get("prompt_tokens", 0)
                total_tokens["completion"] += usage.get("completion_tokens", 0)
                
            except Exception as e:
                logger.log_event("AGENT_ERROR", {
                    "step": steps,
                    "error": str(e),
                    "error_type": "LLM_CALL_FAILED"
                })
                return f"Error calling LLM: {str(e)}"
            
            # Parse thought and action from LLM output
            thought, action_name, action_args = self._parse_action(llm_output)
            
            # Log this step
            logger.log_event("AGENT_STEP", {
                "step": steps,
                "thought": thought,
                "action_name": action_name,
                "action_args": action_args,
                "llm_output": llm_output[:500] if llm_output else ""
            })
            
            # Check for Final Answer
            if "final answer" in llm_output.lower():
                final_answer = self._extract_final_answer(llm_output)
                logger.log_event("AGENT_FINAL_ANSWER", {
                    "step": steps,
                    "answer": final_answer
                })
                break
            
            # Execute tool if action was parsed
            if action_name:
                observation = self._execute_tool(action_name, action_args)
            else:
                # Parsing failed - ask LLM to retry with correct format
                observation = "Error: Could not parse action. Please follow the format: Action: tool_name(param_name=value)"
                logger.log_event("AGENT_PARSE_ERROR", {
                    "step": steps,
                    "llm_output": llm_output[:500],
                    "error": "Failed to extract action"
                })
            
            # Append to history for next iteration
            self.history.append({
                "thought": thought,
                "action": f"{action_name}({action_args})" if action_name else "PARSE_ERROR",
                "observation": observation
            })
            
            steps += 1
        
        # If we hit max_steps without Final Answer, use last observation as answer
        if final_answer is None:
            if self.history:
                final_answer = self.history[-1].get("observation", "Max steps reached without final answer")
            else:
                final_answer = "Max steps reached without generating response"
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Track metrics
        try:
            tracker.track_request(
                provider=self.llm.__class__.__name__,
                model=self.llm.model_name,
                usage={
                    "prompt_tokens": total_tokens["prompt"],
                    "completion_tokens": total_tokens["completion"],
                    "total_tokens": total_tokens["prompt"] + total_tokens["completion"]
                },
                latency_ms=latency_ms
            )
        except Exception as e:
            logger.log_event("AGENT_METRICS_ERROR", {"error": str(e)})
        
        # Log agent end
        logger.log_event("AGENT_END", {
            "steps": steps,
            "success": final_answer is not None,
            "final_answer": final_answer[:200] if final_answer else "",
            "total_tokens": total_tokens["prompt"] + total_tokens["completion"],
            "latency_ms": latency_ms
        })
        
        return final_answer or "No answer generated"

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """
        Execute a tool with the given arguments.
        Routes to the correct tool function and handles errors gracefully.
        
        Args:
            tool_name: Name of the tool to execute
            args_str: String representation of arguments (e.g., "name=John")
        
        Returns:
            String representation of the tool result
        """
        # Check if tool exists
        if tool_name not in TOOLS:
            return f"Error: Unknown tool '{tool_name}'. Available tools: {list(TOOLS.keys())}"
        
        try:
            # Parse arguments (simple parsing: "name=value, id=value2")
            tool_fn = TOOLS[tool_name]
            kwargs = self._parse_tool_args(args_str)
            
            # Call tool
            result_str = tool_fn(**kwargs)
            result = json.loads(result_str)
            
            # Log tool execution
            logger.log_event("TOOL_EXECUTION", {
                "tool": tool_name,
                "args": kwargs,
                "result_status": result.get("status", "unknown")
            })
            
            # Return formatted observation - since tools return JSON, just return the string
            return result_str
        
        except Exception as e:
            error_msg = f"Exception executing tool '{tool_name}': {str(e)}"
            logger.log_event("TOOL_EXECUTION_ERROR", {
                "tool": tool_name,
                "args": args_str,
                "error": str(e)
            })
            return f"Error: {error_msg}"
    
    def _parse_tool_args(self, args_str: str) -> Dict[str, str]:
        """
        Parse tool arguments from string format.
        Handles: "name=value" or "name=value, id=value2"
        
        Args:
            args_str: Argument string from LLM
        
        Returns:
            Dictionary of parsed arguments
        """
        args = {}
        if not args_str or not args_str.strip():
            return args
        
        # Split by comma
        parts = args_str.split(",")
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                # Clean up quotes and whitespace
                key = key.strip().strip('"\'')
                value = value.strip().strip('"\'')
                args[key] = value
        
        return args
    
    def _parse_action(self, llm_output: str) -> tuple:
        """
        Parse thought and action from LLM output.
        Looks for patterns like:
        - Thought: ...
        - Action: tool_name(args)
        
        Args:
            llm_output: Raw output from LLM
        
        Returns:
            Tuple of (thought, action_name, action_args)
        """
        thought = ""
        action_name = None
        action_args = ""
        
        # Extract thought
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", llm_output, re.IGNORECASE | re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
        
        # Extract action using regex
        # Matches: Action: tool_name(args)
        action_match = re.search(r"Action:\s*(\w+)\s*\((.*?)\)", llm_output, re.IGNORECASE)
        
        if action_match:
            action_name = action_match.group(1).strip()
            action_args = action_match.group(2).strip()
        
        return thought, action_name, action_args
    
    def _extract_final_answer(self, llm_output: str) -> str:
        """
        Extract the final answer from LLM output.
        Looks for "Final Answer:" and returns everything after it.
        
        Args:
            llm_output: Raw output from LLM
        
        Returns:
            The extracted final answer
        """
        # Match "Final Answer:" and capture everything after
        match = re.search(r"Final Answer:\s*(.*)", llm_output, re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip()
            # Clean up any remaining formatting
            answer = answer.split("\n")[0] if "\n" in answer else answer
            return answer
        
        return None
    
    def _build_prompt(self, user_input: str) -> str:
        """
        Build the prompt for the current step, including full history.
        
        Args:
            user_input: The original user question
        
        Returns:
            Formatted prompt including user input and history
        """
        prompt = f"User Question: {user_input}\n\n"
        
        if not self.history:
            prompt += "Begin solving the problem."
        else:
            prompt += "Previous steps:\n"
            for i, step in enumerate(self.history, 1):
                prompt += f"\nStep {i}:\n"
                prompt += f"Thought: {step['thought']}\n"
                prompt += f"Action: {step['action']}\n"
                prompt += f"Observation: {step['observation']}\n"
            
            prompt += "\nContinue with the next step (or provide Final Answer if done)."
        
        return prompt
