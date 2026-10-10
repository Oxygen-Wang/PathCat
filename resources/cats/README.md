# 小猫原始图片

`calico/` 保存用户提供的 `PathCat_calico_batch01_batch02.zip` 、`PathCat_calico_batch03_packaged.zip` 、`PathCat_calico_batch04.zip` 及 `PathCat_calico_7states_pack.zip` 中的 47 张透明 PNG 原图，包括基础形象和 46 个动作。第三批补齐成功、错误、离线、开心、兴奋、挥手、说话、困惑、害羞、难过。

应用使用 `quietpet/assets/cat/calico/` 下的 256×256 透明图片，显示时按所选大小缩放。缺少的动作显示该形象的 idle 图；原图保持完整，供后续调整与生成使用。

重新准备应用素材：安装 Pillow 后，在项目根目录运行 `python tools/prepare_cat_assets.py`。应用运行不依赖 Pillow。

右键小猫，通过「小猫形象」切换默认小猫和三花猫；选择会保存。

第四批补齐生气、疲惫、睡觉、伸懒腰、梳毛、吃东西、音乐、探头、跳跃、奔跑。睡觉图片用于现有的 5 分钟无交互睡眠逻辑；其他图片接入动作清单，待对应交互触发。原图完整保留。

七状态包补齐打滚、头晕、箱子、技能拖拽、技能复制、MCP、MCP 错误。技能拖拽与点击复制使用现有触发逻辑；其他素材按动作清单载入，不新增触发行为。
