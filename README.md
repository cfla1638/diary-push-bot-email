# diary-push-bot

一个通过邮件发送“历史上的今天”日记的机器人。

程序会在指定日期读取日记目录，找出所有年份里当天写过的日记，随机选中一篇并发送到指定邮箱；如果当天没有任何候选日记，则不发送。

## 功能

- 扫描按年份组织的 Markdown 日记目录
- 解析 `## <日期>` 格式的日记条目
- 从多个年份的“今天”中随机选择一篇
- 通过 SMTP 发送纯文本邮件
- 支持手动预览、手动发送、内置定时发送

## 技术栈

- Python 3.11+
- UV

## 日记目录格式

日记目录按年份分文件夹，每个月一个 Markdown 文件：

```text
Diary/
├── 2023/
│   ├── 2023-01.md
│   ├── 2023-02.md
│   └── ...
└── 2024/
    └── ...
```

月文件格式示例：

```markdown
# 2024 - 4

## 1 星期六
日记正文……

## 12 星期三 除夕
日记正文……
```

程序会从二级标题开头提取日期，也就是匹配 `## <数字>`。

当前实现只处理规范路径：

- `<日记根目录>/<YYYY>/<YYYY-M[M]>.md`
- `<日记根目录>/<YYYY>/<YYYY-MM>.md`

像索引文件、随笔文件、非年份目录会被忽略。

## 安装

```bash
uv sync
```

## 配置

先复制配置文件：

```bash
cp .env.example .env
```

然后填写 `.env`。

### 通用配置项

```env
DIARY_ROOT=./Diary
RECIPIENT_EMAIL=your-receiver@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_SENDER=your-email@example.com
SMTP_STARTTLS=true
SMTP_SSL=false
SEND_TIME=09:00
TIMEZONE=Asia/Shanghai
```

字段说明：

- `DIARY_ROOT`：日记根目录
- `RECIPIENT_EMAIL`：收件邮箱
- `SMTP_HOST`：SMTP 服务器地址
- `SMTP_PORT`：SMTP 端口
- `SMTP_USERNAME`：SMTP 登录用户名
- `SMTP_PASSWORD`：SMTP 密码或授权码
- `SMTP_SENDER`：发件人地址
- `SMTP_STARTTLS`：是否启用 STARTTLS
- `SMTP_SSL`：是否使用 SSL
- `SEND_TIME`：每日发送时间，格式 `HH:MM`
- `TIMEZONE`：时区，默认 `Asia/Shanghai`

### QQ 邮箱示例

如果使用 QQ 邮箱，推荐配置：

```env
DIARY_ROOT=./Diary
RECIPIENT_EMAIL=your-receiver@example.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=your-qq@qq.com
SMTP_PASSWORD=your-smtp-auth-code
SMTP_SENDER=your-qq@qq.com
SMTP_STARTTLS=false
SMTP_SSL=true
SEND_TIME=09:00
TIMEZONE=Asia/Shanghai
```

注意：

- `SMTP_PASSWORD` 不是 QQ 登录密码，而是 QQ 邮箱开启 SMTP 后生成的授权码
- QQ 邮箱通常使用 `465 + SSL`

### Outlook 示例

```env
DIARY_ROOT=./Diary
RECIPIENT_EMAIL=your-receiver@example.com
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-outlook@example.com
SMTP_PASSWORD=your-password-or-app-password
SMTP_SENDER=your-outlook@example.com
SMTP_STARTTLS=true
SMTP_SSL=false
SEND_TIME=09:00
TIMEZONE=Asia/Shanghai
```

## 使用方法

### 1. 预览今天会发送什么

```bash
uv run diary-push-bot preview --env-file .env
```

这个命令不会真正发邮件，只会打印本次选中的日记和邮件内容。

### 2. 立即执行一次发送

```bash
uv run diary-push-bot send-once --env-file .env
```

### 3. 启动内置定时调度

```bash
uv run diary-push-bot serve --env-file .env
```

程序会常驻运行，并在 `SEND_TIME` 指定的时间发送邮件。

## 运行逻辑

1. 读取 `.env` 配置
2. 根据当前日期定位所有年份中对应月份的月文件
3. 在月文件中查找当天的 `## <日期>` 条目
4. 从候选日记中随机选择一篇
5. 生成纯文本邮件并发送
6. 如果没有候选日记，则跳过发送

## 测试

运行测试：

```bash
uv run pytest
```

当前测试覆盖：

- 多年份候选日记匹配
- 非规范路径忽略
- Markdown 图片行保留
- 无候选时跳过发送
- 定时执行时间计算

## 当前限制

- 邮件为纯文本，不发送附件或内嵌图片
- Markdown 图片链接会按原文保留，不会转成附件
- 内置调度为单进程常驻模式，适合个人使用场景
- Windows 终端下如果出现中文乱码，通常是终端编码问题，不影响邮件逻辑
