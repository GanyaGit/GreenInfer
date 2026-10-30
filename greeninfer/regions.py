# greeninfer/regions.py
# China province-level CO2 intensity data
# Source: CEADs (Carbon Emission Accounts & Datasets), Liu et al. 2022
# Units: gCO2/kWh

CHINA_PROVINCES = {
    # High coal provinces (Northeast + North)
    "Inner Mongolia":  950,
    "Xinjiang":        920,
    "Ningxia":         910,
    "Shanxi":          890,
    "Liaoning":        820,
    "Hebei":           810,
    "Shandong":        800,
    "Heilongjiang":    790,
    "Jilin":           780,
    "Shaanxi":         760,
    # Central / mixed
    "Henan":           740,
    "Anhui":           730,
    "Jiangsu":         700,
    "Hubei":           680,
    "Hunan":           640,
    "Chongqing":       620,
    "Beijing":         600,
    "Tianjin":         590,
    "Shanghai":        570,
    "Zhejiang":        560,
    "Fujian":          530,
    "Jiangxi":         520,
    "Guangdong":       490,
    "Hainan":          460,
    # Hydro-rich Southwest
    "Sichuan":         130,
    "Yunnan":          120,
    "Guizhou":         110,
    "Tibet":            50,
    "Guangxi":         400,
    "Gansu":           650,
    "Qinghai":         100,
}

# National average fallback for China (2023, IEA-consistent)
CHINA_NATIONAL_AVG = 560  # gCO2/kWh