import pytest
from unittest.mock import patch, mock_open
import pandas as pd
from backend.tools import file_operations, data_analysis

# Tests for read_file_content
def test_read_file_content_success(mocker):
    mocker.patch('os.path.isabs', return_value=False)
    mocker.patch('os.path.dirname', return_value='/app/backend')
    mocker.patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    mocker.patch('os.path.commonpath', side_effect=lambda paths: paths[0])
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isfile', return_value=True)
    mocker.patch('builtins.open', mock_open(read_data='file content'))

    result = file_operations.read_file_content.func('test.txt')
    assert "Content of 'test.txt'" in result
    assert 'file content' in result

def test_read_file_content_not_found(mocker):
    mocker.patch('os.path.isabs', return_value=False)
    mocker.patch('os.path.dirname', return_value='/app/backend')
    mocker.patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    mocker.patch('os.path.commonpath', side_effect=lambda paths: paths[0])
    mocker.patch('os.path.exists', return_value=False)

    result = file_operations.read_file_content.func('test.txt')
    assert "Error: File 'test.txt' does not exist" in result

# Tests for write_file_content
def test_write_file_content_success(mocker):
    mocker.patch('os.path.isabs', return_value=False)
    mocker.patch('os.path.dirname', return_value='/app/backend')
    mocker.patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    mocker.patch('os.path.commonpath', side_effect=lambda paths: paths[0])
    mocker.patch('os.makedirs')
    mocker.patch('builtins.open', mock_open())

    result = file_operations.write_file_content.func('test.txt', 'new content')
    assert "Successfully wrote content to 'test.txt'" in result

# Tests for list_files_in_directory
def test_list_files_in_directory_success(mocker):
    mocker.patch('os.path.isabs', return_value=False)
    mocker.patch('os.path.dirname', return_value='/app/backend')
    mocker.patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    mocker.patch('os.path.commonpath', side_effect=lambda paths: paths[0])
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.listdir', return_value=['file.txt', 'subdir'])
    mocker.patch('os.path.getsize', return_value=123)

    # Side effect for os.path.isdir to handle multiple calls
    def isdir_side_effect(path):
        if 'subdir' in path:
            return True
        return False

    mocker.patch('os.path.isdir', side_effect=[True, False, True])

    result = file_operations.list_files_in_directory.func('some_dir')
    assert "[DIR]  subdir/" in result
    assert "[FILE] file.txt (123 bytes)" in result

# Tests for get_file_info
def test_get_file_info_success(mocker):
    mock_stat = mocker.Mock()
    mock_stat.st_size = 456
    mock_stat.st_mtime = 1678886400 # A fixed timestamp

    mocker.patch('os.path.isabs', return_value=False)
    mocker.patch('os.path.dirname', return_value='/app/backend')
    mocker.patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    mocker.patch('os.path.commonpath', side_effect=lambda paths: paths[0])
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.stat', return_value=mock_stat)
    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('time.ctime', return_value='Wed Mar 15 12:00:00 2023')

    result = file_operations.get_file_info.func('test.txt')
    assert "Path: test.txt" in result
    assert "Size: 456 bytes" in result
    assert "Type: File" in result
    assert "Modified: Wed Mar 15 12:00:00 2023" in result

# Tests for DataAnalysisTool
@pytest.fixture
def mock_df():
    return pd.DataFrame({
        'A': [1, 2, 3],
        'B': [4.0, 5.0, 6.0],
        'C': ['foo', 'bar', 'baz']
    })

def test_data_analysis_tool_read_file(mocker, mock_df):
    mocker.patch('pandas.read_csv', return_value=mock_df)
    mocker.patch('pandas.read_excel', return_value=mock_df)

    # Test CSV reading
    df_csv = data_analysis.DataAnalysisTool._read_file('test.csv')
    pd.testing.assert_frame_equal(df_csv, mock_df)

    # Test Excel reading
    df_excel = data_analysis.DataAnalysisTool._read_file('test.xlsx')
    pd.testing.assert_frame_equal(df_excel, mock_df)

def test_analyze_data_summary(mocker, mock_df):
    mocker.patch('backend.tools.data_analysis.DataAnalysisTool._read_file', return_value=mock_df)
    result = data_analysis.DataAnalysisTool.analyze_data.func('test.csv', analysis_type='summary')

    assert result['shape'] == {'rows': 3, 'columns': 3}
    assert result['columns'] == ['A', 'B', 'C']

def test_intelligent_data_visualization(mocker):
    # Mock all external dependencies
    mocker.patch('pandas.read_excel')
    mock_chat_anthropic = mocker.patch('backend.tools.data_analysis.ChatAnthropic')
    mock_llm = mock_chat_anthropic.return_value
    mock_llm.invoke.return_value.content = "pie chart"
    mocker.patch('matplotlib.pyplot.figure')
    mocker.patch('matplotlib.pyplot.savefig')
    mocker.patch('matplotlib.pyplot.close')

    result = data_analysis.intelligent_data_visualization('test.xlsx')

    assert result is not None
    assert 'chart_path' in result
    assert 'strategy' in result
    assert 'pie chart' in result['strategy']
