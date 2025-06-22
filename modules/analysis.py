import jieba
from collections import Counter
import pandas as pd

def keyword_stats(texts, top_n=20):
    # 合併所有評論
    corpus = ' '.join(texts)
    # 分詞（可自行加入停用詞處理）
    words = [w for w in jieba.cut(corpus) if len(w)>1]
    cnt = Counter(words)
    most_common = cnt.most_common(top_n)
    # 轉成 DataFrame
    df = pd.DataFrame(most_common, columns=['keyword','count'])
    return df
