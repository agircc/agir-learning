## 1. 创建一个 process instance
process instance 

## 2. 找到当前要执行的第一个 node
可以根据 process_transitions 来找到第一个 node

process_transtions 上有 process id, from_node_id, to_node_id

根据 process id 找到所有的 process_transitions, 再分析 from 和 to 的 id，先列出来所有的 to ids，再找到不再 to ids 里面的 node id，就是第一个 node

## 3. 根据找到的 node，找到 node 上关联的 process role

## 4. 根据 process role, 找到 user 或者 创建 user
去数据库的 process role user 表里，根据 role id 和 process instance id 查找 process role user，
如果找到了，继续使用，
如果找不到，创建 user 或者找到合适的 user，然后创建 process role user

## 5. 创建 node 对应的 process instance step
让 process role user 根据 user 上的 model 请求对应的 llm 提供，请求时提供当前 node 这个 user 要做的事情，llm 生成对应的 data

将 llm 生成的 data 保存在 process instance step 表上的 comment 字段上

## 6. 找到下一个 node，按照上面的流程 2-5，创建下一个 process instance step
找到这个 step 对应的 user，找到对应的 model，请求响应的 llm

请求 llm 时，提供上一个 process instance step 的 comment 信息

## 7. 依此类推，直到没有下一个 node
