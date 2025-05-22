
增加登录页面：
输入邮箱、发送邮箱验证码、输入验证码后，可以登录。
如果邮箱在 user 表没有存在过，创建 user 记录
邮箱发送服务使用 azure 的服务
邮箱验证码存到 redis

导航有两个菜单：scenarios 和 users
scenarios 菜单，点击后可以查看 scenarios 列表
- scenario 点击后进入到 scenarios 详情，详情页能看到 scenario 的定义，需要查看 agir_db 里面的 scenario 定义，需要展示全部信息，比如有哪些 states、transtions
- scenario 详情页，还要能查看这个 scenario 下面运行过的所有 episodes 列表
- 点击 episode 后，进入 episode 详情页
- 进入 episode 能够看到执行过的 steps
- 点击 step 能查看到 step 的具体内容，以及 step 关联的 conversation

users 菜单, 点击后可以查看 users 列表
- 点击 user 后可以查看这个 user 的所有信息，具体查看 agir_db user 表信息
- user 详情页还能看到 user 的所有 memories，具体信息查看 user_memories 表
- user 详情页还有 chat 入口，点击后打开 chat 页面

chat 页面
- 可以和这个用户聊天
- 聊天页面可以加载之前的所有 conversation 记录
- 聊天时创建数据库的聊天记录

