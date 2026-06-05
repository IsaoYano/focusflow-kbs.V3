# app.py
# ================================================================
# FocusFlow-KBS — Main Application
# Run this file with: python -m streamlit run app.py
# ================================================================
import streamlit as st
import os
import re
from dotenv import load_dotenv

# Load environment variables from the .env file
# This reads your GOOGLE_API_KEY
load_dotenv()

# Import LangChain components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

# Import our project files
from tools import (
    emotional_checkin_tool,
    task_chunking_tool,
    priority_triage_tool,
    distraction_control_tool
)
from knowledge_base import SYSTEM_PROMPT_V2_STRONG

# ================================================================
# PAGE CONFIGURATION
# Sets the browser tab title, icon, and layout
# ================================================================
st.set_page_config(
    page_title="FocusFlow-KBS | ADHD Task Support",
    page_icon="🧠",
    layout="wide"
)

# ================================================================
# SIDEBAR
# ================================================================
with st.sidebar:
    st.title("🧠 FocusFlow-KBS")
    st.caption("ADHD Task Management Support System")
    st.caption("KMK3013 Knowledge-Based Systems | UNIMAS FSKPM")
    st.info("Mode: V3 Final Corrected — post-GDVRR version with session memory, clarification gate, emotional gate, and safer intensity extraction.")
    st.divider()

    st.subheader("📚 Knowledge Base")
    st.metric("Rules", "24", "evidence-based")
    st.metric("Sources", "4", "peer-reviewed")

    with st.expander("🔧 Active Tools"):
        st.write("1. 💙 Emotional Check-In Tool")
        st.write("2. 📋 Task Chunking Tool")
        st.write("3. 🎯 Priority Triage Tool")
        st.write("4. 🌿 Distraction Control Tool")

    with st.expander("📖 Evidence Sources"):
        st.write("• Ogundele & Ayyash (2023) — AIMS Public Health")
        st.write("• Albalawi et al. (2026) — Cureus")
        st.write("• NICE NG87 (2019) — National Clinical Guideline")
        st.write("• Ramos-Galarza et al. (2024) — J. Clinical Medicine")

    with st.expander("🧩 Rule-to-Tool Mapping"):
        st.write("**Emotional Check-In Tool** → A-005, O-005, N-004, R-001")
        st.write("**Task Chunking Tool** → A-001, A-002, A-009, N-002, N-003, R-002")
        st.write("**Priority Triage Tool** → A-003, O-006, N-004, R-001, R-004, A-008")
        st.write("**Distraction Control Tool** → A-002, N-001, O-002")

    st.divider()
    st.warning("⚠️ Not a medical tool. For task management support only.")

    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.cot_steps = []
        st.session_state.last_response = ""
        st.rerun()

# ================================================================
# SESSION STATE INITIALIZATION
# Streamlit resets on every interaction.
# Session state preserves data between interactions.
# ================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "cot_steps" not in st.session_state:
    st.session_state.cot_steps = []

if "last_response" not in st.session_state:
    st.session_state.last_response = ""    

if "agent" not in st.session_state:
    # Build the agent once, store it in session state
    try:
        # 1. Set up the LLM (Gemini)
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2
        )

        # 2. Define all tools available to the agent
        tools = [
            emotional_checkin_tool,     # Priority 1 — emotion must come first
            task_chunking_tool,
            priority_triage_tool,
            distraction_control_tool
        ]

        # 3. Get the ReAct (Reason + Act) agent prompt template
        # This template tells the agent HOW to think and act
        REACT_PROMPT = """
You are FocusFlow-KBS, an explainable agentic knowledge-based system for ADHD-related task management and executive function support.

You have access to the following tools:

{tools}

Use the following format exactly:

Question: the user input
Thought: think about what the user needs based on the expert rules
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
Thought: decide whether another tool is needed
Action: the next action to take, must be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
Thought: I now know the final answer
Final Answer: the final answer to the user

Important system boundaries:
- Do not diagnose ADHD.
- Do not recommend medication.
- Do not provide clinical treatment.
- Only provide task-management and executive-function support.
- If the user shows emotional overwhelm, use the Emotional Check-In Tool before task planning.
- If the task is large or unclear, use the Task Chunking Tool.
- If there are multiple tasks, use the Priority Triage Tool.
- If distraction is medium or high, use the Distraction Control Tool.
- Keep the final answer practical, structured, and easy to follow.

CRITICAL FORMAT RULE:
After every Observation, you must continue using exactly one of these two formats:

Option A, if another tool is needed:
Thought: I need to use another tool.
Action: one of [{tool_names}]
Action Input: the input to the action

Option B, if no more tools are needed:
Thought: I now know the final answer
Final Answer: the final answer to the user

Never write a normal user-facing answer directly after Observation.
Never skip the "Final Answer:" label when ending the response.

CRITICAL EMOTIONAL GATE:
If emotional_checkin_tool returns Intensity 6/10 or higher, HIGH INTENSITY DETECTED, or MODERATE INTENSITY:
- Do NOT call distraction_control_tool, task_chunking_tool, or priority_triage_tool in the same turn.
- Do NOT assume the user completed emotional regulation.
- End immediately using:
Thought: I now know the final answer
Final Answer: ask the user to complete the emotional regulation steps and re-rate their intensity.

Question: {input}
Thought: {agent_scratchpad}
"""

        prompt = PromptTemplate.from_template(REACT_PROMPT)

        # 4. Create the agent
        agent = create_react_agent(llm, tools, prompt)

        # 5. Wrap in executor with verbose=True
        # verbose=True prints the full CoT to the terminal when you run the app
        # return_intermediate_steps=True gives us each step to display in Streamlit
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,                   # Shows CoT in terminal — required for GDVRR
            max_iterations=8,               # Maximum steps before stopping
            handle_parsing_errors=True,     # Prevents crashes on malformed output
            return_intermediate_steps=True  # Returns each step for our CoT display
        )

        st.session_state.agent = agent_executor
        st.success("✅ FocusFlow agent is ready!")

    except Exception as e:
        st.error(f"❌ Setup failed: {e}")
        st.error("Make sure your GOOGLE_API_KEY is set in the .env file.")
        st.info("See the setup guide for how to get a free API key.")
        st.stop()

# ================================================================
# MAIN LAYOUT — Two columns
# ================================================================
col1, col2 = st.columns([3, 2])

# ----------------------------------------------------------------
# LEFT COLUMN: Chat Interface
# ----------------------------------------------------------------
with col1:
    st.header("💬 Chat")

    # Display conversation history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input box
    user_input = st.chat_input(
        "Describe your task... e.g., 'I have a 90-min essay due tomorrow, I feel overwhelmed (8/10), and my house is noisy.'"
    )

    if user_input:
        # Show user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Run agent
        with st.chat_message("assistant"):
            with st.spinner("FocusFlow is thinking... (10-30 seconds)"):
                try:
                    # V3 correction: pass prior conversation history into the model.
                    # The latest user message has already been appended to st.session_state.messages,
                    # so exclude it from history and pass it separately as LATEST USER MESSAGE.
                    recent_messages = st.session_state.messages[:-1][-8:]

                    conversation_history = ""
                    for msg in recent_messages:
                        role = "User" if msg["role"] == "user" else "Assistant"
                        conversation_history += f"{role}: {msg['content']}\n"

                    full_input = f"""
{SYSTEM_PROMPT_V2_STRONG}

CONVERSATION HISTORY:
{conversation_history}

LATEST USER MESSAGE:
{user_input}

IMPORTANT:
Use the conversation history to understand short replies.
If the user gives a short answer like "coding project", "essay", "tomorrow", "panic", or "5/10",
interpret it based on the previous assistant question.

If the user previously gave a task type, remember it.
If the user later says their intensity is 5/10 or below, continue planning the previously mentioned task.
Do not ask for the task again unless no task was mentioned earlier.
"""
                    result = st.session_state.agent.invoke({"input": full_input})

                    response = result.get("output", "Sorry, I could not generate a response.")
                    intermediate = result.get("intermediate_steps", [])

                    st.markdown(response)
                    st.session_state.last_response = response
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })

                    # Format steps for execution trace display
                    steps = []
                    for i, (action, observation) in enumerate(intermediate):
                        observation_text = str(observation)
                        matched_rules = sorted(set(re.findall(r"\b[A-Z]-\d{3}\b", observation_text)))

                        steps.append({
                            "step": i + 1,
                            "tool": action.tool,
                            "input": str(action.tool_input),
                            "output": observation_text,
                            "log": str(getattr(action, "log", "")),
                            "matched_rules": matched_rules
                        })

                    st.session_state.cot_steps = steps

                except Exception as e:
                    st.error(f"Error: {e}")
                    error_text = str(e).lower()

                    if "resource_exhausted" in error_text or "quota" in error_text or "429" in error_text:
                        st.error("Quota/rate limit reached. Wait a few minutes, then try again. Your API key is working.")
                        st.info("This is a technical API limit, not a KBS reasoning anomaly. Wait before testing again.")
                    elif "not_found" in error_text or "models/" in error_text:
                        st.error("Model name issue. Try another available Gemini model.")
                    elif "api" in error_text or "key" in error_text:
                        st.error("API key issue. Check your .env file.")
                    
# RIGHT COLUMN: Agent Execution Trace
# ----------------------------------------------------------------
with col2:
    st.header("🔍 Agent Execution Trace")
    st.caption("CoT-style tool-call trace for GDVRR Deconstruct: selected tool, action input, observation, and matched rules.")

    if st.session_state.cot_steps:
        for step in st.session_state.cot_steps:
            with st.expander(
                f"Step {step['step']}: {step['tool']}",
                expanded=True
            ):
                st.markdown("**TRACE LOG (agent Thought/Action text):**")
                if step.get("log"):
                    st.code(step["log"], language="text")
                else:
                    st.info(f"Agent selected tool: `{step['tool']}`")

                st.markdown("**ACTION INPUT (sent to tool):**")
                st.code(str(step["input"]), language="text")

                st.markdown("**MATCHED RULES FOUND IN TOOL OUTPUT:**")
                if step.get("matched_rules"):
                    st.success(", ".join(step["matched_rules"]))
                else:
                    st.warning("No explicit rule ID detected in this tool output.")

                st.markdown("**OBSERVATION PREVIEW (tool response):**")
                output_preview = step["output"][:700]
                if len(step["output"]) > 700:
                    output_preview += "\n... [preview truncated; full text available below]"
                st.success(output_preview)

                with st.expander("Full observation"):
                    st.code(step["output"], language="text")
        st.divider()

        # Raw trace for copy-pasting into Table 1
        with st.expander("📋 Raw Trace (Copy for Table 1)"):
            st.caption("Copy the relevant segment and paste into your Table 1 — Deconstruct column")
            raw = ""
            for s in st.session_state.cot_steps:
                raw += f"=== STEP {s['step']} ===\n"
                raw += f"TRACE LOG:\n{s.get('log', '')}\n"
                raw += f"ACTION: {s['tool']}\n"
                raw += f"ACTION INPUT:\n{s['input']}\n"
                raw += f"MATCHED RULES: {', '.join(s.get('matched_rules', [])) if s.get('matched_rules') else 'No explicit rule ID detected'}\n"
                raw += f"OBSERVATION:\n{s['output']}\n\n"

            raw += "=== FINAL ANSWER ===\n"
            raw += st.session_state.last_response

            st.text_area("", raw, height=500)
    else:
        st.info(
            "Send a message to generate the V3 final execution trace.\n\n"
            "**Complex test scenario to try:**\n"
            "'I have to finish a report at 2am. I am stressed 9/10, sleepy, "
            "the task was not supposed to be mine, the person in charge is not replying, "
            "and someone keeps ragebaiting me. I also have another small task due tomorrow.'"
        )

# ================================================================
# FOOTER
# ================================================================
st.divider()
st.caption(
    "FocusFlow-KBS V3 Final Corrected | KMK3013 Knowledge-Based Systems | UNIMAS FSKPM | "
    "Sources: Ogundele & Ayyash (2023), Albalawi et al. (2026), NICE NG87 (2019), Ramos-Galarza et al. (2024) | "
    "⚠️ Task management support only. Not a clinical or medical tool."
)
