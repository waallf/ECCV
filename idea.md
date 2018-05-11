# 已完成
1. 训练DSSD,利用kmeans计算ratio aspect  
2. 由于样本不均衡。所以将11类归为4类，统计发现样本还是不均衡  
3. 将<truncation>,<occlusion>不为0的全部放入第11类（不充当正样本，也不充当负样本）





---
# 未完成  
1. 改变每个特征图中设定anchors框的大小
2. 将输入改为1024  
3. 切图  
4. 使用残差网络，并修改残差结构（按论文）
5. 训练R-FCN  
6. 看能否实现Single-Shot Bidirectional Pyramid Networks for High-Quality Object Detection
7. 使用新的损失函数
