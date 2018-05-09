# 利用k-means计算anchors
[利用k-means计算anchors](https://blog.csdn.net/hrsstudy/article/details/71173305?utm_source=itdadao&utm_medium=referral#__NO_LINK_PROXY__)
## 距离计算公式：
d = 1 - IOU(box,centroid),centroid是作为聚类中心的框  
[代码](https://github.com/waallf/ECCV/blob/master/k-means_anchors.py)

## 怎么使用计算出的聚类中心：  
k-means 计算出了n个中心(box 的长和宽)  
* 选取聚类中心个数，如果loss可以减小很多的话，就增加一个聚类中心(dssd中使用了7个cluster)  
* 看哪个产生的中心所占比例最高  
* 计算出这个中心的长宽比，加入aspect ratio  
## eccv annoations数据格式：
bbox_left>        ：预测左上角X坐标  
bbox_top          ：预测左上角y坐标  
bbox_width        ：框的宽度  
bbox_height       ：框的高度  
score             ：预测对象的置信度，训练集中给的值是0或1，1表示这个框需要求学习，0则放弃  
object_category   ：类别  
truncation        ：对象在框外所占的比例，被设置为-1  

