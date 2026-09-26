# QuizScanner 原生安卓教师端

版本 2.0.1，应用标识 cn.quizscanner.teacher。课堂、测验、更多、摄像头预览和卡片识别均为本地实现，主 Activity 为 NativeActivity；工程不再包含旧 WebView Activity。

## 构建

需要 JDK 17、Gradle 9.4.1、Android SDK 36。设置 JAVA_HOME、ANDROID_HOME、ANDROID_USER_HOME、GRADLE_USER_HOME 后执行 gradle assembleDebug --no-daemon。

使用 AGP 9.2.0 内置 Kotlin、Compose 编译插件 2.2.10、Material 3 Expressive、CameraX 与 OpenCV ArUco。首次下载依赖需要网络。

现有升级签名位于本地 signing/classroom.keystore，不随源码压缩包提供。此文件保持私有；在其他电脑独立构建时，可修改 signingConfigs 使用自己的签名，但将无法直接覆盖安装已有 APK。

## 功能与连接

电脑版本至少 3.2.0。手机在更多中扫一扫，扫描电脑教师页“手机扫码连接”的二维码。二维码包含地址和一次服务运行的配对码；电脑服务重启后需要重新配对。

同一网络可以是电脑热点、同一路由器或手机热点。扫码不能代替 Wi-Fi 接入，也不能绕过校园网络的设备隔离。

默认使用后置摄像头；更多中可手动选择可用后置镜头。按实际竖直方向判读，旋转时通过重力传感器和传感器图像坐标变换补偿。平放拍摄可切换“按屏幕上方判读”。

答案队列、测验缓存和离线课堂保存至应用私有 SQLite 数据库；离线课堂当前采用不限时流程，补传为独立场次，不改变电脑正在进行的课堂。

## 验收边界

本地构建与签名检查通过，不代表真机摄像头与手机网络已经验收。必须用实际安卓手机检查横竖屏、镜头、对焦、距离、生命周期、二维码连接与结束后重新开启摄像头。
