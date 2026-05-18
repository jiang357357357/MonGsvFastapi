#!/bin/bash

# MonGSV 项目打包脚本 (Linux)
# 功能：使用 tar/7z 打包项目，排除 .monconfig 中指定的文件

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 查找工作区根目录（向上查找 .monconfig 标记文件）
find_workspace_root() {
    local dir="$1"
    while [[ "$dir" != "/" ]]; do
        if [[ -f "$dir/.monconfig" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# 自动查找工作区根目录
WORKSPACE_ROOT=$(find_workspace_root "$SCRIPT_DIR")
if [[ -z "$WORKSPACE_ROOT" ]]; then
    echo "[警告] 未找到 .monconfig 工作区标记文件，使用脚本所在目录作为源目录"
    WORKSPACE_ROOT="$SCRIPT_DIR"
fi

# 默认配置
OUTPUT_FILE=""
SOURCE_DIR="$WORKSPACE_ROOT"
USE_TAR=false

# 显示帮助
show_help() {
    echo "MonGSV 项目打包工具 (Linux)"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -o, --output <文件>    输出文件名 (默认: MonGSV_YYYYMMDD_HHMMSS.tar.gz)"
    echo "  -s, --source <目录>    源目录 (默认: 当前目录)"
    echo "  -t, --tar              使用 tar.gz 格式 (默认: 7z)"
    echo "  -h, --help             显示帮助"
    echo ""
    echo "示例:"
    echo "  $0                              # 使用默认设置打包"
    echo "  $0 -o backup.7z                 # 指定输出文件"
    echo "  $0 -t -o backup.tar.gz          # 使用 tar.gz 格式"
    echo ""
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -s|--source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        -t|--tar)
            USE_TAR=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 设置默认输出文件名
if [[ -z "$OUTPUT_FILE" ]]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    if $USE_TAR; then
        OUTPUT_FILE="MonGSV_${TIMESTAMP}.tar.gz"
    else
        OUTPUT_FILE="MonGSV_${TIMESTAMP}.7z"
    fi
fi

# 转换为绝对路径
OUTPUT_FILE="$(cd "$(dirname "$OUTPUT_FILE")" && pwd)/$(basename "$OUTPUT_FILE")"

echo ""
echo "=================================================="
echo "  MonGSV 项目打包工具 (Linux)"
echo "=================================================="
echo ""
echo "  源目录: $SOURCE_DIR"
echo "  输出文件: $OUTPUT_FILE"
echo "  格式: $([ "$USE_TAR" = true ] && echo "tar.gz" || echo "7z")"
echo ""

# 检查源目录
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "错误: 源目录不存在: $SOURCE_DIR"
    exit 1
fi

# 从 .monconfig 读取排除规则
MONCONFIG_FILE="$SOURCE_DIR/.monconfig"
EXCLUDE_PATTERNS=()

if [[ -f "$MONCONFIG_FILE" ]]; then
    echo "[读取] 排除规则: $MONCONFIG_FILE"
    
    # 读取 [pack] 部分的 EXCLUDE_PATTERNS
    in_pack_section=false
    while IFS= read -r line || [[ -n "$line" ]]; do
        # 检测 [pack] 部分开始
        if [[ "$line" =~ ^\[pack\] ]]; then
            in_pack_section=true
            continue
        fi
        
        # 检测其他部分开始，结束 [pack] 部分
        if [[ "$line" =~ ^\[.*\] ]] && $in_pack_section; then
            break
        fi
        
        # 在 [pack] 部分内读取 EXCLUDE_PATTERNS
        if $in_pack_section; then
            # 跳过 EXCLUDE_PATTERNS= 行本身
            if [[ "$line" =~ ^EXCLUDE_PATTERNS= ]]; then
                continue
            fi
            
            # 读取缩进的模式行
            line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            # 跳过空行和注释
            [[ -z "$line" ]] && continue
            [[ "$line" =~ ^# ]] && continue
            
            # 移除尾部斜杠
            line=$(echo "$line" | sed 's/\/$//')
            
            EXCLUDE_PATTERNS+=("$line")
        fi
    done < "$MONCONFIG_FILE"
    
    echo "  已加载 ${#EXCLUDE_PATTERNS[@]} 条排除规则"
    echo ""
    
    # 显示被排除的大文件夹
    echo "[分析] 被排除的大文件夹:"
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        if [[ -d "$SOURCE_DIR/$pattern" ]]; then
            size=$(du -sh "$SOURCE_DIR/$pattern" 2>/dev/null | cut -f1)
            echo "  [排除] $pattern (${size})"
        fi
    done
    echo ""
    
    # 显示将要打包的文件夹大小（排除子目录后）
    echo "[分析] 将要打包的文件夹:"
    total_size=0
    for item in "$SOURCE_DIR"/*; do
        if [[ -d "$item" ]]; then
            basename=$(basename "$item")
            # 检查是否在排除列表中
            excluded=false
            for pattern in "${EXCLUDE_PATTERNS[@]}"; do
                if [[ "$basename" == "$pattern" ]] || [[ "$basename" == $pattern ]]; then
                    excluded=true
                    break
                fi
            done
            
            if ! $excluded; then
                # 计算实际大小（排除子目录）
                # 使用 find 和 du 计算，排除匹配的文件/目录
                size_bytes=0
                while IFS= read -r -d '' file; do
                    rel_path="${file#$SOURCE_DIR/}"
                    # 检查是否在排除列表中
                    skip=false
                    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
                        if [[ "$rel_path" == $pattern ]] || [[ "$rel_path" == $pattern/* ]] || [[ "$rel_path" == */$pattern/* ]]; then
                            skip=true
                            break
                        fi
                    done
                    if ! $skip; then
                        file_size=$(stat -c%s "$file" 2>/dev/null)
                        size_bytes=$((size_bytes + file_size))
                    fi
                done < <(find "$item" -type f -print0 2>/dev/null)
                
                # 转换为人类可读格式
                if [[ $size_bytes -gt 1073741824 ]]; then
                    size=$(echo "scale=1; $size_bytes/1073741824" | bc)G
                elif [[ $size_bytes -gt 1048576 ]]; then
                    size=$(echo "scale=1; $size_bytes/1048576" | bc)M
                elif [[ $size_bytes -gt 1024 ]]; then
                    size=$(echo "scale=1; $size_bytes/1024" | bc)K
                else
                    size="${size_bytes}B"
                fi
                
                total_size=$((total_size + size_bytes))
                echo "  [包含] $basename (${size})"
            fi
        fi
    done
    
    # 显示总大小
    if [[ $total_size -gt 1073741824 ]]; then
        total=$(echo "scale=1; $total_size/1073741824" | bc)G
    elif [[ $total_size -gt 1048576 ]]; then
        total=$(echo "scale=1; $total_size/1048576" | bc)M
    elif [[ $total_size -gt 1024 ]]; then
        total=$(echo "scale=1; $total_size/1024" | bc)K
    else
        total="${total_size}B"
    fi
    echo ""
    echo "  [总计] 预估打包大小: ${total}"
    echo ""
    
else
    echo "[警告] 未找到 .monconfig 文件"
    echo ""
fi

# 执行打包
echo "[打包] 开始打包..."
echo ""

cd "$SOURCE_DIR"

if $USE_TAR; then
    # 使用 tar.gz
    echo "使用 tar.gz 格式打包..."
    
    # 构建排除参数
    EXCLUDE_ARGS=()
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        EXCLUDE_ARGS+=(--exclude="$pattern")
    done
    
    # 打包
    tar -czf "$OUTPUT_FILE" "${EXCLUDE_ARGS[@]}" .
    
else
    # 使用 7z
    if ! command -v 7z &> /dev/null; then
        echo "错误: 未找到 7z，请安装 p7zip-full"
        echo "  Ubuntu/Debian: sudo apt install p7zip-full"
        exit 1
    fi
    
    echo "使用 7z 格式打包..."
    
    # 构建排除参数
    EXCLUDE_ARGS=()
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        EXCLUDE_ARGS+=(-xr!"$pattern")
    done
    
    # 打包
    7z a -t7z -m0=lzma2 -mx=9 "${EXCLUDE_ARGS[@]}" "$OUTPUT_FILE" .
fi

# 显示结果
echo ""
echo "=================================================="
if [[ -f "$OUTPUT_FILE" ]]; then
    FILE_SIZE=$(du -h "$OUTPUT_FILE" 2>/dev/null | cut -f1)
    echo "[结果] ✓ 打包成功"
    echo "  输出文件: $OUTPUT_FILE"
    echo "  文件大小: $FILE_SIZE"
else
    echo "[结果] ✗ 打包失败"
    exit 1
fi
echo "=================================================="
echo ""
