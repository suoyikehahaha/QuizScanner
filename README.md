# QuizScanner 简体中文版

电脑端 **3.2.1** · 原生安卓教师端 **2.0.1**

学生使用纸质 A/B/C/D 答题卡，教师用安卓手机扫描，电脑浏览器实时展示题目和所选班级的作答情况。学生无需使用手机。

> **原作者为 Piotr Kajor（[PiotrKajor](https://github.com/PiotrKajor)）。本仓库是 [PiotrKajor/QuizScanner](https://github.com/PiotrKajor/QuizScanner) 的 Fork，由 [suoyikehahaha](https://github.com/suoyikehahaha) 维护简体中文与原生安卓扩展。原项目的 MIT 许可证及版权声明完整保留。** 详见 [作者与项目来源](NOTICE.md)。

## 下载

最新发行见 **[Releases](https://github.com/suoyikehahaha/QuizScanner/releases/latest)**。

| 文件 | 用途 |
|---|---|
| `QuizScanner-Windows-3.2.1.zip` | Windows 免安装包，含 EXE、使用说明、导入模板和许可证 |
| `QuizScanner-Windows-3.2.1.exe` | 单独下载电脑程序 |
| `QuizScanner-Android-2.0.1.apk` | 原生安卓教师端，支持 Android 6.0 及以上、ARM64/ARMv7 |
| `QuizScanner-source-v3.2.1.zip` | 本版完整源码 |
| `THIRD-PARTY-LICENSES.zip` | 随发行保留的第三方许可证 |
| `SHA256SUMS.txt` | 下载文件的 SHA-256 校验值 |

**电脑端与手机端应一起更新。** 本次为原生安卓扫码反馈修正版，已完成构建、签名和本地运行检查；实际手机的横竖屏、镜头、识别距离、网络连接及延迟尚未完成真机验收。见 [验证记录](docs/VERIFICATION.md)。APK 沿用本地既有测试签名，与本项目原 1.0.9 APK 的应用标识、签名一致。

## 快速开始

1. 在电脑启动程序，点击启动服务，默认端口为 `8012`。
2. 手机安装 APK，让手机与电脑连接同一网络。
3. 电脑教师页点击顶部 **手机扫码连接**，选择手机可访问的电脑网络地址。
4. 手机进入 **更多 → 扫一扫**，扫描二维码。APP 自动读取 IP、端口和配对码，随后同步班级与测验。
5. 选择班级与测验，开始本题作答。学生将所选字母朝上举起答题卡，教师扫码收集答案。

电脑无法开启热点时，两台设备可连接同一路由器，或让电脑连接手机热点。二维码负责传递连接信息，两端仍需网络互通。电脑服务重启后请重新扫码配对。

教师面板 `http://localhost:8012/teacher` · 投影大屏 `/board` · 题目编辑器 `/editor`。改变端口后使用相应地址。

## 本版功能

- 原生 Compose Material 3 Expressive 页面，课堂、测验、更多三个入口；支持横向分页与手势切换。
- CameraX 本地全屏预览、OpenCV ArUco 本地识别、可用后置镜头选择和点按对焦。
- 扫码画面实时显示卡片轮廓、学生姓名与所选答案；区分识别中、待提交、已提交和离线记录，并保留最近两名学生的反馈。
- 默认以实际竖直方向判断选项，结合重力传感器与图像坐标变换补偿旋转；平放拍摄可切换屏幕上方模式。方向表现仍需真机验收。
- 红色按钮结束作答、关闭摄像头并呈现选项人数和学生姓名；下一题自动开启扫码。
- 电脑、手机和投影端使用统一切题命令；过期答案拒收、重复事件去重。
- 先创建班级再导入 CSV/XLSX 名单，保留原学号并独立管理卡片号；开始后仅展示所选班级。
- DOCX 提取四选一题目；阅读材料与子题分开保存，投影可独立查看材料。
- 题干与选项支持重点标记，大屏预览复用真实投影布局；保留浅色中国风、深色及黑板主题。
- 同题重答替换旧成绩，历次记录保留；按班级与场次生成报告，包含未扫码学生。
- 电脑课堂快照自动保存、历史课堂恢复；手机缓存测验和名单，离线课堂补传为独立场次。
- 支持 PDF、XLSX、CSV、HTML、JSON、TXT 报告和班级答题卡 PDF。

现有 ArUco 答题卡继续沿用相同字典与边缘映射。连接二维码与学生答题卡是两种不同的识别入口。

## 使用与开发

- [完整中文使用说明](docs/USAGE.md)
- [更新说明](CHANGELOG.md)
- [构建与发布](docs/BUILD.md)
- [原生安卓工程](android-app/README.md)
- [验证记录与已知边界](docs/VERIFICATION.md)
- [第三方依赖许可](THIRD_PARTY_NOTICES.md)
- [原项目说明文档](docs/UPSTREAM-README.md)

从源码启动电脑端：

```shell
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python launcher.py
# 无桌面模式：python -m quizscanner --port 8012 --no-camera --no-browser
```

Windows 源码启动需要含 Tkinter 的 Python。安卓构建需要 JDK 17、Android SDK 36 与 Gradle 9.4.1。

## 数据与贡献

运行时的名单、学生答案、媒体、课堂快照及报告保存在本机 `data` 目录或应用私有存储中，不随源码上传。本仓库只含虚构的示例名单与示例测验。APK 卸载会清除本机缓存，升级时请优先覆盖安装。

欢迎通过 [本仓库 Issues](https://github.com/suoyikehahaha/QuizScanner/issues) 反馈问题。摄像头问题请附手机型号、安卓版本、横竖屏方向、复现步骤和去除真实学生信息的截图。提交代码前请阅读 [贡献说明](CONTRIBUTING.md)。

## 许可证与致谢

原项目版权 `Copyright (c) 2026 Piotr Kajor`，许可证为 **[MIT](LICENSE)**。本衍生版本保留该声明；第三方依赖遵循各自许可证。感谢原作者提供 QuizScanner 的基础设计、答题卡识别与桌面测验实现。
