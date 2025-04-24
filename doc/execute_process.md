## 1. 创建一个 process instance
process instance 

## 2. 找到当前要执行的 node

## 3. 根据找到的 node，找到 node 上关联的 process role

## 根据 process role, 找到 user 或者 创建 user
去数据库的 process role user 表里，根据 role id 和 process instance id 查找 process role user，
如果找到了，继续使用，
如果找不到，创建 user 或者找到合适的 user，然后创建 process role user

## 创建 node 对应的 process instance step，让 process role 提供对应的 data