import numpy as np
'''
x : Fiyat listesi
y : Son karşılaştırılabilir değer.
z : Geçmiş karşılaştırılabilir değer.

# find_high_high
( x : fiyat listesi, y : son yüksek değer, z : tarihi yüksek değer )
Hem yakın zamana hem de geçmişe göre görülen en yüksek değeri döndür veya Yok.

# bul_yüksek
( x : fiyat listesi, y : son en yüksek )
Görülen en yüksek değeri döndür veya Yok.

# find_low_high
( x : fiyat listesi, y : son yüksek değer, z : tarihi yüksek değer )
Yakın zamanda görülen ancak geçmişte daha düşük olan en yüksek değeri döndür veya Yok.

# find_low_low
( x : fiyat listesi, y : son dip, z : tarihi düşük değer )
Hem yakın zamana hem de geçmişe göre görülen en düşük değeri veya Yok'u döndürün.

# bul_düşük
( x : fiyat listesi, y : son dip )
Görülen en düşük değeri veya Yok'u döndürün.

# find_high_low
( x : fiyat listesi, y : son dip, z : tarihi düşük değer )
Yakın zamanda görülen ancak geçmişte daha yüksek olan en düşük değeri döndür veya Yok.
'''
## Yüksek kurulumlar
find_high_high  = lambda x, y, z: x.max() if z < x.max() > y else None
find_high       = lambda x, y: x.max() if x.max() > y else None
find_low_high   = lambda x, y, z: x.max() if z > x.max() > y else None
## Düşük kurulum
find_low_low    = lambda x, y, z: x.min() if z > x.min() < y else None
find_low        = lambda x, y: x.min() if x.min() < y else None
find_high_low   = lambda x, y, z: x.min() if z < x.min() < y else None

"""
Ticaret kalıpları.

"""
class pattern_W:
    def __init__(self):
        self.required_points = 4
        self.result_points = 1 # Yalnızca sonucu görüntülemek için test için gereklidir.
        self.segment_span = 4
        self.price_point = 0

    def check_condition(self, point_set):
        if point_set[3] > point_set[1] > point_set[2] > point_set[0]:
            print('part 1')
            if point_set[1] > point_set[2]+((point_set[3]-point_set[2])/2) and (100 - ((point_set[0]/point_set[2])*100)) < 1.2:
                print('part 2')
                return(True)

        return(False)