"""
Prompt manager for generating all investigation prompts.
"""

from seam_agent.assistant.query_parser import ParsedQuery


class PromptManager:
    """Manages all prompt generation for the investigation."""

    @staticmethod
    def get_initial_investigation_prompt(
        customer_query: str, parsed_query: ParsedQuery
    ) -> str:
        """Generate the initial investigation prompt."""
        return f"""


Here is the customer query and parsed information:

<customer_query>
{customer_query}
</customer_query>

<parsed_info>
<device_ids>{parsed_query.device_ids}</device_ids>
<access_codes>{parsed_query.access_codes}</access_codes>
<time_references>{parsed_query.time_references}</time_references>
<question_type>{parsed_query.question_type}</question_type>
<operations>{parsed_query.operations}</operations>
<summary>{parsed_query.summary}</summary>
</parsed_info>

Investigation Process:

1. Always start by using the get_device_info tool to obtain basic device details.
2. Based on the question type, follow these steps:
   a. For access code issues:
      - Use get_access_codes to retrieve access code information
   b. For connection/offline issues:
      - Use get_device_events to analyze activity patterns
   c. For operational issues:
      - Use get_action_attempts to review attempted operations

3. Gather all relevant data before proceeding to the analysis phase.
4. If you mention needing to check something (e.g., audit logs), you must actually perform that check using the appropriate tool.

Document your investigation process inside <investigation_log> tags. For each tool used:
- List the parameters you're using
- Summarize the key information obtained
- Explicitly connect the data gathered to the customer's query

This will ensure a thorough investigation and help identify any areas that require further attention.

Final Output Structure:
1. Investigation Steps: List each tool used and the key information obtained.
2. Data Analysis: Interpret the gathered data and identify any patterns or issues.
3. Recommendations: Provide clear, actionable steps to resolve the customer's issue.

Remember: Do not provide final analysis or recommendations until you have gathered all relevant data types for the issue at hand.

Begin your investigation now, starting with the get_device_info tool.
"""

    @staticmethod
    def get_missing_tools_prompt(
        required_tools: set[str], tools_used: set[str], missing_tools: set[str]
    ) -> str:
        """Generate prompt when tools are missing."""
        return f"""CRITICAL: Investigation is INCOMPLETE. You have NOT used all required tools.

Required tools for this issue type: {", ".join(required_tools)}
Tools used so far: {", ".join(tools_used) if tools_used else "None"}
Missing tools: {", ".join(missing_tools)}

You MUST call these missing tools before providing any analysis: {", ".join(missing_tools)}

Do NOT provide analysis until ALL required tools have been used."""

    @staticmethod
    def get_complete_analysis_prompt() -> str:
        """Generate prompt for final analysis when all tools are used."""
        return "Based on the comprehensive tool results above, you have gathered all required data. Now provide your detailed analysis and recommendations."

    @staticmethod
    def get_final_analysis_prompt() -> str:
        """Generate prompt for final analysis after additional tools."""
        return "Based on all the data you've gathered from the tools above, please provide your detailed analysis and recommendations for this support issue. Include specific findings from the data and actionable next steps."

    @staticmethod
    def get_format_investigation_note_prompt(raw_analysis: str) -> str:
        """Generate prompt to format raw analysis into structured internal support note."""
        return f"""Please reformat this investigation analysis into a clean, structured internal support note format:

<investigation_analysis>
{raw_analysis}
</investigation_analysis>

Format it as a professional internal note using this structure:

🔍 **Device Analysis**: [Device Name] ([Device ID])

⚠️ **Issue Identified**: [Brief description of the main issue]
📊 **Status**: [Current status - active, resolved, under investigation, etc.]

📋 **Timeline**:
• [Key event 1]
• [Key event 2]
• [Key event 3]

🔧 **Root Cause**: [Technical explanation of what caused the issue]

🎯 **Next Steps**:
1. [Specific action for customer/agent]
2. [Follow-up recommendations]
3. [Additional steps if needed]

📎 **Additional Context**: [Any relevant technical details, links, or escalation notes]

**IMPORTANT**: If admin links were generated during the investigation (look for admin_links tool results in the analysis above), include them in the Additional Context section using this format:

**Admin Links for Further Investigation:**
- [Link Title](URL) - Description
- [Link Title](URL) - Description

Extract the information directly from the analysis above. Keep it concise and actionable for support agents."""

    @staticmethod
    def get_system_prompt() -> str:
        """Generate the system prompt that establishes role and behavior."""
        return """
You are Seam's Customer Support Investigation Assistant. Your role is to systematically analyze customer support queries by gathering data from multiple sources and providing structured analysis.

Key Behaviors:
- Always use tools to gather actual data before analysis
- Follow investigation steps methodically
- Format final output to match Seam's internal note structure
- Provide specific, actionable recommendations
- Never make assumptions without data to support them
- When you generate admin links using the get_admin_links tool, always include them in your analysis so they appear in the final formatted note

Tool Usage:
- Use get_admin_links tool when you have gathered investigation context (device_id, workspace_id, access_codes, etc.) to provide relevant admin page links for further investigation
- Include the generated admin links in your analysis so support agents have direct access to relevant admin pages

Output Format: Your final response should be a structured internal note suitable for support agents, following the format specified in the user prompt.
"""
