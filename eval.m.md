# evalDET.m  
* datasetPath - dataset path  
* resPath     - result path  

# saveAnnoRes  
* call    dropObjectsInIgr 选择符合条件的bbox  
* gt中 score 等于1的变为0，等于0的变为1  
* 对预测框得分进行排序，分高的在前面  
# dropObjectsInIgr  
* 没看懂  
# calcAccuracy  
```
for 每一类：
  for iou 阈值： 
    for maxDets:
      for 所有图像：
        取出等于第n类的图像数据（gt 与预测）
        evalRes（）
      计算AR（返回的AR shape是（10,10,4））
     计算AP（返回的shape 是（10,10））
```  
# evalRes  

···
for 所有预测框：
  for gt框：
    if m==1 and !mul #m==1 #表示该GT正类已经已经匹配过，mul表示是否可以多次匹配
      contiune
    end
    if bstm!=0 and m==-1: # bstm不等于0表示预测框已经被匹配过，m==-1，表示这个gt框是第0类，gt和预测框都是拍过续的，如果遇到第0类，表示后面都是第0类了，就不用再往下循环  
      break  
    end
    判断iou是否达到阈值  
    if m==0: #表示在gt中是需要评分的类别
      bstm =1
    else:
      btsm =-1
      
···

