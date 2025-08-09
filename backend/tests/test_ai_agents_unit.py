import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from backend.ai_agent_simple import SimpleAIAgent
from backend.ai_agent_direct import DirectAIAgent

# Fixture for SimpleAIAgent
@pytest.fixture
def simple_agent(mocker):
    mocker.patch('backend.ai_agent_simple.ChatAnthropic')
    mocker.patch('backend.ai_agent_simple.read_file_content')
    mocker.patch('backend.ai_agent_simple.write_file_content')
    mocker.patch('backend.ai_agent_simple.list_files_in_directory')
    mocker.patch('backend.ai_agent_simple.get_file_info')

    agent = SimpleAIAgent()
    agent.llm = MagicMock()
    agent.llm_with_tools = MagicMock()
    return agent

# Tests for SimpleAIAgent
@pytest.mark.asyncio
async def test_simple_agent_analyze_no_tools(simple_agent):
    # Mock the LLM response to not use any tools
    mock_response = MagicMock()
    mock_response.tool_calls = []
    mock_response.content = "Final answer"
    simple_agent.llm_with_tools.ainvoke = AsyncMock(return_value=mock_response)

    events = []
    async for event in simple_agent.analyze("hello"):
        events.append(event)

    assert any(e['type'] == 'final_result' and e['content'] == 'Final answer' for e in events)

@pytest.mark.asyncio
async def test_simple_agent_analyze_with_tool_call(simple_agent, mocker):
    # Mock the LLM to first call a tool, then give a final answer
    tool_call_response = MagicMock()
    tool_call_response.tool_calls = [{'name': 'read_file_content', 'args': {'file_path': 'test.txt'}, 'id': '123'}]
    tool_call_response.content = ""

    final_response = MagicMock()
    final_response.tool_calls = []
    final_response.content = "File content is hello"

    simple_agent.llm_with_tools.ainvoke = AsyncMock(side_effect=[
        tool_call_response,
        final_response
    ])

    # Mock the tool function
    mocker.patch('backend.ai_agent_simple.read_file_content.invoke', return_value="hello")

    events = []
    async for event in simple_agent.analyze("read test.txt"):
        events.append(event)

    assert any(e['type'] == 'tool_use' and e['content'] == 'Using tool: read_file_content' for e in events)
    assert any(e['type'] == 'tool_result' for e in events)
    assert any(e['type'] == 'final_result' and e['content'] == 'File content is hello' for e in events)

# Fixture for DirectAIAgent
@pytest.fixture
def direct_agent(mocker):
    mocker.patch('backend.ai_agent_direct.FileSearchTool._run', return_value="Found files:\n1. test.csv (test.csv, 123 bytes)")
    mocker.patch('backend.ai_agent_direct.UniversalDataTool._run', return_value="Analyzed data")
    mocker.patch('backend.ai_agent_direct.CodeExecutor._run', return_value="Code executed")
    mocker.patch('anthropic.Anthropic')
    agent = DirectAIAgent()
    return agent

# Tests for DirectAIAgent
@pytest.mark.asyncio
async def test_direct_agent_analyze_search(direct_agent):
    events = []
    async for event in direct_agent.analyze("find csv files"):
        events.append(event)

    assert any(e['type'] == 'tool_use' and 'Searching for files' in e['content'] for e in events)
    assert any(e['type'] == 'final_result' for e in events)

@pytest.mark.asyncio
async def test_direct_agent_analyze_visualize(direct_agent, mocker):
    # Mock the LLM decision to run python code
    llm_decision = {
        "action": "run_python",
        "code": "print('hello')",
        "explain": "Generating a chart"
    }
    mocker.patch('backend.ai_agent_direct.DirectAIAgent._decide_action_with_llm', return_value=llm_decision)

    # Mock os functions
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.getsize', return_value=123)
    mocker.patch('os.path.join', return_value='/app/test-directory/chart.png')


    events = []
    async for event in direct_agent.analyze("visualize data in test.csv", attached_file_paths=['test.csv']):
        events.append(event)

    assert any(e['type'] == 'tool_result' and 'Code executed' in e['content'] for e in events)
    assert any(e['type'] == 'final_result' and 'Generating a chart' in e['content'] for e in events)
