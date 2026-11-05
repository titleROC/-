# 发布 PDF 的工作流（.github/workflows/release.yml）用的辅助函数，由各步骤 source。
# GitHub 接口偶尔会临时出错（例如 HTTP 500），所以每个网络操作都重试几次；
# 查询 Release 是否存在时，只有确定是 404 才算“不存在”，临时故障不会被误当成“还没有 Release”。
# 需要的环境变量：TAG（Release 的标签名）、GITHUB_REPOSITORY；可选 RETRY_WAIT（首次重试前等待的秒数，默认 15）。

# retry 命令 [参数…]：失败时依次等 1、2、3 倍 RETRY_WAIT 秒后重试，共试 4 次
retry() {
  local i wait="${RETRY_WAIT:-15}"
  for i in 1 2 3 4; do
    "$@" && return 0
    [ "$i" -lt 4 ] || break
    echo "::warning::第 $i 次失败，$((i * wait)) 秒后重试：$*" >&2
    sleep "$((i * wait))"
  done
  echo "::error::试了 4 次仍然失败：$*" >&2
  return 1
}

# release_state：Release「$TAG」已发布时输出 yes，GitHub 明确回答不存在（HTTP 404）时输出 no；
# 其他错误重试后仍失败时返回非零。用 state="$(release_state)" 调用，出错时 set -e 会让步骤失败。
release_state() {
  local i wait="${RETRY_WAIT:-15}" err
  err="$(mktemp)"
  for i in 1 2 3 4; do
    if gh api "repos/$GITHUB_REPOSITORY/releases/tags/$TAG" --silent 2> "$err"; then
      rm -f "$err"; echo yes; return 0
    fi
    if grep -q 'HTTP 404' "$err"; then
      rm -f "$err"; echo no; return 0
    fi
    cat "$err" >&2
    [ "$i" -lt 4 ] || break
    echo "::warning::查询 Release「$TAG」第 $i 次失败，$((i * wait)) 秒后重试" >&2
    sleep "$((i * wait))"
  done
  rm -f "$err"
  echo "::error::无法确定 Release「$TAG」是否存在" >&2
  return 1
}

# list_assets 文件：把 Release 中现有 PDF 的文件名写入文件（每次重试都重写，不会重复）
list_assets() {
  gh release view "$TAG" --json assets --jq '.assets[].name' > "$1"
}

# create_release 说明文件 提交：新建没有附件的 Release（一次小请求，不会像带附件创建那样先留下草稿）。
# GitHub 偶尔在已经建好之后仍返回错误，所以失败时再查一次，已经存在就算成功。
create_release() {
  gh release create "$TAG" --title "高考物理真题 PDF" --notes-file "$1" --target "$2" \
    || [ "$(release_state)" = yes ]
}
