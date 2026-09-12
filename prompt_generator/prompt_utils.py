"""提示词文本解析工具（纯函数）

从 server.py 抽出的文本解析/清洗函数，无外部服务依赖，便于单元测试与复用。
"""

import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# 整体被 Markdown 代码围栏包裹的输出（模型常用 ```xml ... ``` 包裹结果）
_CODE_FENCE_RE = re.compile(r"^```[A-Za-z0-9_-]*[ \t]*\r?\n(.*?)\r?\n?```\s*$", re.DOTALL)


def fix_unicode_escapes(text):
    """修复Unicode和十六进制转义序列"""
    if not isinstance(text, str):
        logger.warning(f"fix_unicode_escapes接收到非字符串类型: {type(text)}")
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            else:
                text = str(text)
        except Exception as e:
            logger.error(f"转换为字符串失败: {str(e)}")
            return str(text)

    # 如果没有转义序列，直接返回
    if '\\x' not in text and '\\u' not in text and '%' not in text:
        return text

    try:
        # 尝试修复不同类型的编码问题

        # 1. 处理 \uXXXX 格式
        def replace_unicode(match):
            try:
                code = match.group(1)
                if len(code) == 4:  # \uXXXX 格式
                    return chr(int(code, 16))
                return match.group(0)
            except Exception as e:
                logger.warning(f"Unicode替换失败: {str(e)}")
                return match.group(0)

        # 2. 处理 \xXX 格式
        def replace_hex(match):
            try:
                code = match.group(1)
                if len(code) == 2:  # \xXX 格式
                    return bytes.fromhex(code).decode('utf-8')
                return match.group(0)
            except Exception as e:
                logger.warning(f"Hex替换失败: {str(e)}")
                return match.group(0)

        # 3. 处理URL编码 %XX 格式
        def replace_url_encoding(match):
            try:
                code = match.group(1)
                if len(code) == 2:  # %XX 格式
                    return bytes.fromhex(code).decode('utf-8')
                return match.group(0)
            except Exception as e:
                logger.warning(f"URL编码替换失败: {str(e)}")
                return match.group(0)

        # 先处理 \uXXXX 格式
        fixed_text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
        # 再处理 \xXX 格式
        fixed_text = re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex, fixed_text)
        # 再处理 %XX 格式
        fixed_text = re.sub(r'%([0-9a-fA-F]{2})', replace_url_encoding, fixed_text)

        # 检查是否有明显的乱码字符（替换字符或控制字符）
        if '\ufffd' in fixed_text or any(ord(c) < 32 and c not in '\r\n\t' for c in fixed_text):
            logger.debug("检测到可能的乱码，尝试其他修复方法")

            # 方法1: latin1 -> utf-8 转换
            try:
                latin1_fixed = text.encode('latin1').decode('utf-8', errors='replace')
                if not any(c == '\ufffd' for c in latin1_fixed):
                    logger.debug("latin1 -> utf-8转换成功")
                    return latin1_fixed
            except Exception as e:
                logger.error(f"latin1到utf-8转换失败: {str(e)}")

            # 方法2: 尝试JSON解析（处理双重转义）
            try:
                # 尝试解析JSON字符串，处理双重转义的情况
                # 将转义字符处理为JSON字符串格式
                json_str = '"' + text.replace('"', '\\"') + '"'
                json_fixed = json.loads(json_str)
                if not any(c == '\ufffd' for c in json_fixed):
                    logger.debug("JSON解析修复成功")
                    return json_fixed
            except Exception as e:
                logger.debug(f"JSON解析修复失败: {str(e)}")

            # 方法3: 移除无效字符
            try:
                # 移除所有控制字符和替换字符
                cleaned_text = ''.join(c for c in fixed_text if ord(c) >= 32 or c in '\r\n\t')
                logger.debug("移除了无效字符")
                return cleaned_text
            except Exception as e:
                logger.error(f"移除无效字符失败: {str(e)}")

        # 如果修复后的文本看起来合理，使用它
        if not any(c == '\ufffd' for c in fixed_text):
            return fixed_text

        # 如果所有方法都失败，返回原始文本
        logger.warning("所有修复方法都失败，返回原始文本")
        return text
    except Exception as e:
        logger.error(f"修复编码失败: {str(e)}")
        return text


def strip_code_fences(text: str) -> str:
    """若文本整体被 Markdown 代码围栏（```xml ... ```）包裹，剥去最外层围栏。

    只处理"围栏包住全文"的情况；正文中间出现的代码块不受影响。
    """
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    match = _CODE_FENCE_RE.match(stripped)
    return match.group(1) if match else text


def extract_between_tags(tag: str, text: str, strip: bool = True) -> List[str]:
    """从文本中提取指定标签之间的内容

    支持以下格式:
    1. 完整的XML标签: <tag>content</tag>
    2. 只有开始标签: <tag>content（取到文本末尾，自动剥去尾部代码围栏）
    3. 开始标签带属性: <tag attr="x">content</tag>
    4. 闭合标签含空白: </tag >
    5. 标签名可能包含空格
    6. 标签名大小写不敏感
    7. 兼容标签名单复数形式

    Args:
        tag: 标签名
        text: 要处理的文本
        strip: 是否去除结果中的首尾空白字符,默认为True

    Returns:
        包含标签内容的列表
    """
    try:
        # 确保文本是字符串类型
        if not isinstance(text, str):
            logger.warning(f"Text is not a string: {type(text)}")
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            else:
                text = str(text)

        # 检查文本是否是有效的UTF-8字符串
        try:
            text.encode('utf-8').decode('utf-8')
        except UnicodeError:
            # 如果不是有效的UTF-8字符串，尝试修复
            try:
                # 尝试以latin1解码再编码为utf-8
                text = text.encode('latin1').decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f"尝试修复文本编码失败: {str(e)}")

        # 检查文本是否包含Unicode转义序列，如果有则尝试修复
        if '\\u' in text or '\\x' in text:
            text = fix_unicode_escapes(text)

        # 剥去包裹全文的代码围栏，避免 ``` 混入未闭合标签的提取结果
        text = strip_code_fences(text)

        # 处理标签名中可能包含的空格
        tag_pattern = tag.replace(" ", r"\s+")

        # 生成单数和复数形式的模式
        # 如果标签已经是复数形式，生成单数形式；如果是单数形式，生成复数形式
        tags_to_try = [tag_pattern]

        # 检查标签是否以's'结尾
        if tag_pattern.endswith('s'):
            # 如果是复数形式，添加单数形式
            singular_tag = tag_pattern[:-1]
            tags_to_try.append(singular_tag)
        else:
            # 如果是单数形式，添加复数形式
            plural_tag = tag_pattern + 's'
            tags_to_try.append(plural_tag)

        matches = []

        # 尝试每个标签形式
        for current_tag in tags_to_try:
            # 开标签允许携带属性，闭合标签允许尾随空白
            open_tag = f"<{current_tag}(?:\\s[^>]*)?>"
            close_tag = f"</{current_tag}\\s*>"

            # 尝试匹配完整的XML标签
            complete_pattern = f"{open_tag}(.+?){close_tag}"
            current_matches = re.findall(complete_pattern, text, re.DOTALL | re.IGNORECASE)

            # 如果没有找到完整标签，取开始标签到文本末尾的全部内容。
            # 注意：不能用 (?=<|$) 非贪婪截断，否则会在 Instructions 内的
            # <tool>、<thinking> 等子标签处提前截断，导致保存内容丢失。
            if not current_matches:
                incomplete_pattern = f"{open_tag}([\\s\\S]*)"
                current_matches = re.findall(incomplete_pattern, text, re.IGNORECASE)

            if current_matches:
                matches.extend(current_matches)
                logger.debug(f"找到标签 {current_tag} 的匹配: {len(current_matches)}个")
                break  # 找到匹配后可以停止尝试其他形式

        if not matches:
            logger.debug(f"未找到标签 {tag} 或其单复数形式的匹配")
            return []

        logger.debug(f"提取标签 {tag}（含单复数形式），找到 {len(matches)} 个匹配")
        if matches:
            logger.debug(f"第一个匹配内容长度: {len(matches[0])}")

        # 移除重复的匹配结果
        unique_matches = list(dict.fromkeys(matches))

        # 处理每个匹配结果，确保它们是有效的UTF-8字符串
        processed_matches = []
        for m in unique_matches:
            if m:
                # 确保匹配结果是有效的UTF-8字符串
                try:
                    if isinstance(m, bytes):
                        m = m.decode('utf-8', errors='replace')
                    # 检查并修复可能的Unicode转义序列
                    if '\\u' in m or '\\x' in m:
                        m = fix_unicode_escapes(m)
                    # 根据strip参数决定是否去除空白字符
                    processed_matches.append(m.strip() if strip else m)
                except Exception as e:
                    logger.error(f"处理匹配结果时出错: {str(e)}")
                    processed_matches.append(m if isinstance(m, str) else str(m))

        return processed_matches

    except Exception as e:
        logger.error(f"Error extracting tags: {str(e)}")
        return []


def extract_variables(text: str) -> Set[str]:
    """提取文本中的所有变量名

    支持三种格式:
    1. {$VARIABLE} - 标准格式
    2. {{VARIABLE}} - 双大括号格式
    3. ${VARIABLE} - 美元符号格式

    Args:
        text: 要处理的文本

    Returns:
        变量名集合
    """
    # 匹配三种格式的变量
    standard_vars = set(re.findall(r'\{\$([A-Za-z0-9_]+)\}', text))
    double_brace_vars = set(re.findall(r'\{\{([A-Za-z0-9_]+)\}\}', text))
    dollar_vars = set(re.findall(r'\$\{([A-Za-z0-9_]+)\}', text))

    # 合并所有格式的结果
    return standard_vars.union(double_brace_vars).union(dollar_vars)


def find_free_floating_variables(prompt: str) -> List[str]:
    """检测提示词中的浮动变量

    Args:
        prompt: 提示词文本

    Returns:
        浮动变量列表（在XML标签外的变量）
    """
    variable_usages = re.findall(r'\{\$[A-Z0-9_]+\}', prompt)
    free_floating_variables = []

    for variable in variable_usages:
        preceding_text = prompt[:prompt.index(variable)]
        open_tags = set()

        i = 0
        while i < len(preceding_text):
            if preceding_text[i] == '<':
                if i + 1 < len(preceding_text) and preceding_text[i + 1] == '/':
                    closing_tag = preceding_text[i + 2:].split('>', 1)[0]
                    open_tags.discard(closing_tag)
                    i += len(closing_tag) + 3
                else:
                    opening_tag = preceding_text[i + 1:].split('>', 1)[0]
                    open_tags.add(opening_tag)
                    i += len(opening_tag) + 2
            else:
                i += 1

        if not open_tags:
            free_floating_variables.append(variable)

    return free_floating_variables


def parse_sections(text: str, tags: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """按标签列表提取章节，用于校验模型输出是否符合标签契约。

    Args:
        text: 模型输出文本
        tags: 期望出现的标签名列表

    Returns:
        (sections, missing)：
        - sections: {标签名: 提取到的第一个匹配内容}
        - missing: 未能提取到内容的标签名列表
    """
    sections: Dict[str, str] = {}
    missing: List[str] = []
    for tag in tags:
        found = extract_between_tags(tag, text)
        if found and found[0]:
            sections[tag] = found[0]
        else:
            missing.append(tag)
    return sections, missing


def apply_tool_guidance(prompt: str, tools: Optional[List[str]] = None) -> str:
    """为 Metaprompt 生成指令追加「工具使用规范」要求（MCP 工具 / Skills 场景）。

    兼容性保证：tools 为 None 或全为空行时，原样返回 prompt——
    与不选择工具的旧版本行为逐字节一致，不影响既有变量/示例的生成质量。

    Args:
        prompt: 已注入 {{TASK}} 的完整 Metaprompt 文本
        tools: 用户声明的可用工具列表，每项格式如 "web_search — 联网搜索最新资料"

    Returns:
        处理后的提示词文本
    """
    if not tools:
        return prompt
    lines = [t.strip() for t in tools if t and t.strip()]
    if not lines:
        return prompt

    tool_block = "\n".join(f"- {line}" for line in lines)
    addendum = f"""

<available_tools>
The AI assistant in the following task has access to these external tools (MCP tools / skills):
{tool_block}
</available_tools>

Additional requirement: when writing the instructions, additionally include a
<tool_usage> section inside the <Instructions> that defines:
- When to use each listed tool, and when to answer directly without tools
- The order and combination of tool calls when multiple tools are needed
- How to handle tool failures, timeouts, or empty results
- A call budget (e.g., the maximum number of invocations) to avoid loops
Tools not listed in <available_tools> must never be mentioned in the instructions."""

    return prompt + addendum
