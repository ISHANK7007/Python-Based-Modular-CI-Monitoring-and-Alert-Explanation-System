# 🧾 CI Analysis Report: OOM Issues  
*Generated: 2023-06-15 14:30:45*  
*Applied Filter: `label=OOM`*

---

## 📊 Summary

- **Total OOM Issues**: 37  
- **High Confidence ( > 0.8 )**: 28  
- **Medium Confidence ( 0.5 – 0.8 )**: 6  
- **Low Confidence ( < 0.5 )**: 3

---

## ✅ High Confidence OOM Issues

### 🔹 Job #4567 – Kubernetes Deployment Test

- **Confidence**: `0.95`  
- **Segment**: [Lines 234–250](#evidence-4567)  
- **Analysis**:  
  Container exceeded the memory limit of **512MB**, peaking at **738MB** during test execution.
