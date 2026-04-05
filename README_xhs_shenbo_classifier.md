# 申博帖子分类工具

这个工具适合做“公开可访问页面”的信息整理，目标是把和以下主题相关的帖子筛出来并分类：

- 新传专业
- 香港博士申请
- 内地博士申请
- `DIY / 半DIY / 中介`

它更像一个“公开帖子整理器”，而不是一个绕过平台限制的爬虫。

## 合规边界

请只处理你有权访问的内容，比如：

- 你手动整理好的公开帖子链接
- 你本地保存的 HTML 页面
- 合法搜索结果中拿到的公开页面

这个脚本不包含以下能力：

- 绕过登录
- 绕过签名、验证码、风控、频率限制
- 抓取私有内容

## 环境准备

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4
```

## 用法

### 方式 1：直接输入公开链接

```bash
python3 xhs_shenbo_classifier.py \
  --url "https://example.com/post1" \
  --url "https://example.com/post2"
```

### 方式 2：从文本文件读取链接

准备一个 `urls.txt`，每行一个公开链接：

```text
https://example.com/post1
https://example.com/post2
```

运行：

```bash
python3 xhs_shenbo_classifier.py --url-file urls.txt
```

### 方式 3：批量读取本地 HTML

```bash
python3 xhs_shenbo_classifier.py --input-dir ./html_pages
```

也可以单独指定多个文件：

```bash
python3 xhs_shenbo_classifier.py \
  --html-file ./html_pages/a.html \
  --html-file ./html_pages/b.html
```

## 输出结果

默认会生成两个文件：

- `xhs_shenbo_classified.csv`
- `xhs_shenbo_summary.json`

仓库里还放了两个演示样例，你可以先直接跑：

```bash
python3 xhs_shenbo_classifier.py --input-dir ./sample_html
```

### CSV 主要字段

- `title`: 标题
- `content`: 抽取到的正文
- `is_relevant`: 是否与目标主题强相关
- `primary_track`: 主分类
- `region`: 申请地区
- `service_mode`: 服务模式
- `service_detail`: 服务细分
- `content_type`: 帖子类型
- `stage_tags`: 涉及阶段
- `school_tags`: 命中的院校标签
- `matched_keywords`: 命中的关键词
- `reason`: 分类理由摘要

## 当前分类规则

### `primary_track`

- `hk_phd_new_media`: 新传 + 香港博士
- `cn_phd_new_media`: 新传 + 内地博士
- `mixed_new_media_phd`: 同时提到港博和内地博
- `other`: 主题不够明确

### `region`

- `hong_kong`
- `mainland`
- `mixed`
- `unknown`

### `service_mode`

- `diy`: 明确提到自己申请、无中介、全DIY
- `semi_diy`: 部分自己做，部分找人改文书或咨询
- `agency`: 明确提到中介、机构、付费服务
- `unknown`

### `service_detail`

- `full_self_managed`: 基本自己完成全流程
- `essay_only`: 主要购买文书修改/润色
- `consulting_only`: 主要购买定位或咨询
- `mixed_support`: 半DIY但支持形式混合
- `full_service`: 机构全程代办
- `unspecified_paid_service`: 明确付费，但帖子没说清服务边界

### `content_type`

- `experience`: 经验贴、上岸总结、时间线
- `help_request`: 求助、求定位、求建议
- `promotion`: 服务推广类内容
- `general`: 普通讨论

### `stage_tags`

- `background`: 背景条件
- `school_selection`: 选校定位
- `supervisor_contact`: 套磁/联系导师
- `materials`: 文书材料
- `interview`: 面试
- `result`: 录取结果

## 你可以怎么扩展

最常见的扩展方式有三种：

1. 增加关键词
   直接修改 [xhs_shenbo_classifier.py](/Users/czh/Documents/Playground/xhs_shenbo_classifier.py) 顶部的关键词列表。

2. 细化分类
   例如把 `service_mode` 再拆成：
   - `diy`
   - `semi_diy_consulting_only`
   - `semi_diy_essay_only`
   - `agency_full_service`

3. 增加学校维度
   例如单独识别：
   - 港大
   - 港中文
   - 港科大
   - 北大
   - 清华
   - 中传

## 一个实用工作流

如果你的目标是系统整理“新传申博经验贴”，建议这样做：

1. 先手动或通过合规方式收集公开帖子链接
2. 跑这个脚本做第一轮筛选
3. 打开 CSV，按 `is_relevant = True` 过滤
4. 再按 `region` 和 `service_mode` 分组
5. 最后人工复核边界样本，补关键词

## 局限

- 不同网站 HTML 结构差异很大，正文抽取不是百分百稳定
- `DIY / 半DIY / 中介` 目前是规则分类，适合第一轮整理，不等于最终人工判断
- 如果帖子写得很隐晦，可能会漏判或误判

如果你希望，我下一步可以继续帮你做两个增强版本之一：

1. 增加“学校名、导师名、是否有科研、是否跨专业”的更细标签
2. 增加“二次精分类”，把 `半DIY` 再拆得更细
