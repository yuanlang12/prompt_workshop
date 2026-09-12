"""prompt_utils 纯函数的单元测试

运行方式（仓库根目录）:
    pip install -r requirements-dev.txt
    python -m pytest tests/ -v
"""

import pytest

from prompt_utils import (
    apply_tool_guidance,
    extract_between_tags,
    extract_variables,
    find_free_floating_variables,
    fix_unicode_escapes,
    parse_sections,
    strip_code_fences,
)


class TestExtractBetweenTags:
    def test_complete_tag(self):
        text = "前文 <prompt>这是提示词内容</prompt> 后文"
        assert extract_between_tags("prompt", text) == ["这是提示词内容"]

    def test_multiple_occurrences_dedup(self):
        text = "<v>A</v><v>B</v><v>A</v>"
        assert extract_between_tags("v", text) == ["A", "B"]

    def test_unclosed_tag_takes_rest_of_text(self):
        # 回归：未闭合标签不能在子标签处提前截断
        text = "<Instructions>\n步骤一 <tool>toolA</tool>\n步骤二 <thinking>think</thinking>\n"
        result = extract_between_tags("Instructions", text)
        assert len(result) == 1
        assert "<tool>toolA</tool>" in result[0]
        assert "步骤二" in result[0]

    def test_case_insensitive(self):
        assert extract_between_tags("prompt", "<PROMPT>x</PROMPT>") == ["x"]

    def test_plural_and_singular(self):
        assert extract_between_tags("prompts", "<prompt>x</prompt>") == ["x"]
        assert extract_between_tags("prompt", "<prompts>x</prompts>") == ["x"]

    def test_tag_name_with_space(self):
        assert extract_between_tags("Writing prompt", "<Writing  prompt>x</Writing prompt>") == ["x"]

    def test_open_tag_with_attributes(self):
        # 模型可能输出 <prompt lang="zh"> 这类带属性的标签
        assert extract_between_tags("prompt", '<prompt lang="zh">中文内容</prompt>') == ["中文内容"]

    def test_close_tag_with_whitespace(self):
        assert extract_between_tags("prompt", "<prompt>x</prompt >") == ["x"]

    def test_code_fenced_whole_output(self):
        text = "```xml\n<prompt>围栏里的内容</prompt>\n```"
        assert extract_between_tags("prompt", text) == ["围栏里的内容"]

    def test_unclosed_tag_with_trailing_fence(self):
        # 未闭合标签 + 尾部围栏：不应把 ``` 带进结果
        text = "```\n<prompt>内容\n```"
        result = extract_between_tags("prompt", text)
        assert result == ["内容"]

    def test_missing_tag_returns_empty(self):
        assert extract_between_tags("prompt", "没有任何标签") == []

    def test_nested_same_name_takes_first_close(self):
        text = "<prompt>a<prompt>b</prompt>c</prompt>"
        # 懒惰匹配取第一对完整闭合的标签（既有行为，测试用于锁定）
        assert extract_between_tags("prompt", text) == ["a<prompt>b"]

    def test_no_strip(self):
        assert extract_between_tags("v", "<v>  x  </v>", strip=False) == ["  x  "]


class TestParseSections:
    def test_all_present(self):
        text = "<Planning initial draft>计划</Planning initial draft>\n<writing prompt>内容</writing prompt>"
        sections, missing = parse_sections(text, ["Planning initial draft", "writing prompt"])
        assert missing == []
        assert sections["Planning initial draft"] == "计划"
        assert sections["writing prompt"] == "内容"

    def test_missing_reported(self):
        sections, missing = parse_sections("<a>x</a>", ["a", "b"])
        assert sections == {"a": "x"}
        assert missing == ["b"]


class TestExtractVariables:
    def test_three_formats(self):
        text = "{$TOPIC} 和 {{GRADE_LEVEL}} 以及 ${ORIGINAL_TEXT}"
        assert extract_variables(text) == {"TOPIC", "GRADE_LEVEL", "ORIGINAL_TEXT"}

    def test_dedup_and_case(self):
        assert extract_variables("{$VAR} {$VAR} {$var2}") == {"VAR", "var2"}

    def test_no_variables(self):
        assert extract_variables("普通文本") == set()


class TestFindFreeFloatingVariables:
    def test_variable_inside_tag_is_not_free(self):
        prompt = "<context>\n{$CONTEXT}\n</context>\n{$TOPIC}"
        assert find_free_floating_variables(prompt) == ["{$TOPIC}"]

    def test_all_free_without_tags(self):
        assert find_free_floating_variables("{$A} {$B}") == ["{$A}", "{$B}"]


class TestStripCodeFences:
    def test_strips_outer_fence(self):
        assert strip_code_fences("```xml\n<p>x</p>\n```") == "<p>x</p>"

    def test_plain_text_unchanged(self):
        assert strip_code_fences("<p>x</p>") == "<p>x</p>"

    def test_inner_fence_unchanged(self):
        text = "说明\n```python\nprint(1)\n```\n结尾"
        assert strip_code_fences(text) == text


class TestFixUnicodeEscapes:
    def test_unicode_escape(self):
        assert fix_unicode_escapes("hello \\u4f60\\u597d") == "hello 你好"

    def test_plain_text_unchanged(self):
        assert fix_unicode_escapes("plain text") == "plain text"

    def test_non_string_input(self):
        assert fix_unicode_escapes(None) == "None"


class TestApplyToolGuidance:
    """核心兼容性保证：不声明工具时，生成提示词与旧版本逐字节一致"""

    def test_none_returns_identical(self):
        assert apply_tool_guidance("BASE", None) == "BASE"

    def test_empty_list_returns_identical(self):
        assert apply_tool_guidance("BASE", []) == "BASE"

    def test_blank_lines_only_returns_identical(self):
        assert apply_tool_guidance("BASE", ["", "   "]) == "BASE"

    def test_tools_appended_with_guidance(self):
        out = apply_tool_guidance("BASE", ["web_search — 联网搜索"])
        assert out.startswith("BASE")
        assert "<available_tools>" in out
        assert "web_search — 联网搜索" in out
        assert "<tool_usage>" in out

    def test_blank_lines_filtered(self):
        out = apply_tool_guidance("BASE", ["", "a_tool — 查询资料", " "])
        block = out.split("<available_tools>")[1].split("</available_tools>")[0]
        tool_lines = [l for l in block.splitlines() if l.strip().startswith("- ")]
        assert tool_lines == ["- a_tool — 查询资料"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
