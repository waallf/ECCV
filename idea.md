# 已完成
1. 训练DSSD,利用kmeans计算ratio aspect  
2. 由于样本不均衡。所以将11类归为4类，统计发现样本还是不均衡  
3. 将<truncation>,<occlusion>不为0的全部放入第11类（不充当正样本，也不充当负样本）
4. 使用新的损失函数  
5. 做思维导图  
6. 统计默认的anchors与bbox的iou大于一个阈值的个数
 
7. 将输入改为1024 (无法训练)
8. 切图  
9.数据分析表加颜色
10.看评分方法
11. 切成512 后需要筛选样本
---
# 未完成  
1. 改变每个特征图中设定anchors框的大小（一开始的想法是将初始的anchors变小，但是由于bbox较小，这样在计算anchors与bbox时的iou就会变小）  

6. 看能否实现Single-Shot Bidirectional Pyramid Networks for High-Quality Object Detection  
（用训练好的SSD来更新anchors,怎么用位置的回归来更新anchors，来使得只改变anchors长宽的情况下，增加iou，而不用改变anchors的中心点坐标）
 怎样用loss来更新anchors，来获得更好的初始框(只能在refineDEt上修改了)
 





  



4. 使用残差网络，并修改残差结构（按论文）
5. 训练R-FCN  

  
4.显示结果时与GT作比较，和官网的结果比较  
  


