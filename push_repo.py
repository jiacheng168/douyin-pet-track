#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_repo.py —— 把整个 douyin-pet-track 技能目录推送到 GitHub 公共仓库。

用法:
    GITHUB_TOKEN=ghp_xxx python push_repo.py \
        [--repo douyin-pet-track] [--rename-from douyin-cat-track] \
        [--delete scripts/run.py]

说明:
    - 走 GitHub REST API (api.github.com)，用 curl 子进程调用（沙箱内需 --ssl-no-revoke）。
    - 遍历技能目录，递归上传所有文件（保持相对路径）。
    - 可选：--rename-from 先把旧仓库改名（保留仓库身份）；--delete 删除仓库内的残留文件。
    - 令牌仅来自环境变量 GITHUB_TOKEN，不落盘。
"""
import os
import sys
import json
import base64
import tempfile
import argparse
import subprocess

API = "https://api.github.com"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# 不上传的本地文件（脚本自身、无关产物）
SKIP = {"push_repo.py", "push_to_github.py"}


def curl(method, path, token, body=None):
    cmd = [
        "curl", "-sS", "-m", "40", "--ssl-no-revoke",
        "-X", method,
        "-H", "Authorization: Bearer " + token,
        "-H", "Accept: application/vnd.github+json",
        "-w", "\nHTTP_STATUS:%{http_code}",
        API + path,
    ]
    tmp = None
    if body is not None:
        # 大文件 base64 后作为 -d 参数会超 Windows 命令行长度上限(206)，改为从临时文件读取
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        tf.write(json.dumps(body, ensure_ascii=False))
        tf.close()
        tmp = tf.name
        cmd += ["-H", "Content-Type: application/json", "-d", "@" + tmp]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    out = p.stdout.decode("utf-8", "replace")
    if "\nHTTP_STATUS:" in out:
        payload, _, status = out.rpartition("\nHTTP_STATUS:")
        return int(status.strip()), payload.strip()
    return None, out


def walk_files(root):
    res = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if os.path.basename(full) in SKIP:
                continue
            res.append((rel, full))
    return sorted(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="douyin-pet-track")
    ap.add_argument("--rename-from", default=None, help="若存在旧仓库名，先改名（保留身份）")
    ap.add_argument("--delete", nargs="*", default=[], help="仓库内需要删除的残留文件路径")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--desc", default="宠物赛道抖音爆款对标工具 / Douyin pet-vertical viral-content benchmarking skill")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("ERROR: 请设置环境变量 GITHUB_TOKEN")

    st, who = curl("GET", "/user", token)
    if st != 200:
        sys.exit("ERROR: 获取用户信息失败 HTTP %s\n%s" % (st, who[:500]))
    owner = json.loads(who).get("login")
    print("[ok] 已登录 GitHub 用户:", owner)

    # 0) 改名（可选）
    if args.rename_from and args.rename_from != args.repo:
        st_r, r = curl("PATCH", "/repos/%s/%s" % (owner, args.rename_from),
                       token, {"name": args.repo, "description": args.desc})
        if st_r == 200:
            print("[ok] 仓库已改名: %s -> %s" % (args.rename_from, args.repo))
        else:
            print("[warn] 改名失败 HTTP %s: %s" % (st_r, r[:300]))

    # 1) 建仓库（已存在则跳过）
    st, res = curl("POST", "/user/repos", token, {
        "name": args.repo, "description": args.desc,
        "private": args.private, "auto_init": False,
    })
    if st == 201:
        print("[ok] 仓库已创建: https://github.com/%s/%s" % (owner, args.repo))
    elif st == 422:
        print("[skip] 仓库已存在，直接上传")
    else:
        sys.exit("ERROR: 创建仓库失败 HTTP %s\n%s" % (st, res[:500]))

    # 2) 上传文件
    for rel, full in walk_files(SKILL_DIR):
        with open(full, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        st_get, exist = curl("GET", "/repos/%s/%s/contents/%s" % (owner, args.repo, rel), token)
        body = {"message": "add " + rel, "content": b64, "branch": "main"}
        if st_get == 200:
            body["sha"] = json.loads(exist)["sha"]
        st_put, put_res = curl("PUT", "/repos/%s/%s/contents/%s" % (owner, args.repo, rel), token, body)
        if st_put in (200, 201):
            print("[ok] 上传:", rel)
        else:
            print("[fail] 上传失败 HTTP %s: %s" % (st_put, put_res[:300]))

    # 3) 删除残留（可选）
    for dpath in args.delete:
        st_g, dexist = curl("GET", "/repos/%s/%s/contents/%s" % (owner, args.repo, dpath), token)
        if st_g == 200:
            sha = json.loads(dexist)["sha"]
            st_d, dres = curl("DELETE", "/repos/%s/%s/contents/%s" % (owner, args.repo, dpath),
                              token, {"message": "remove stale " + dpath, "sha": sha, "branch": "main"})
            if st_d in (200, 204):
                print("[ok] 已删除残留:", dpath)
            else:
                print("[warn] 删除残留失败 HTTP %s: %s" % (st_d, dres[:200]))

    print("\n完成。仓库地址: https://github.com/%s/%s" % (owner, args.repo))


if __name__ == "__main__":
    main()
