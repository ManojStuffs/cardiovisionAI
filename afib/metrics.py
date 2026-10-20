"""Sensitivity / specificity / F1 on the AFib class (as promised on the 'Expected Outcome' slide)."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score, average_precision_score


def report(y_true, prob, threshold=0.5) -> dict:
    y_true = np.asarray(y_true).astype(int)
    pred = (np.asarray(prob).ravel() >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    sens = tp / max(tp + fn, 1)
    spec = tn / max(tn + fp, 1)
    ppv = tp / max(tp + fp, 1)
    f1 = 2 * ppv * sens / max(ppv + sens, 1e-12)
    return dict(threshold=float(threshold), sensitivity=sens, specificity=spec, precision=ppv, f1=f1,
                accuracy=(tp + tn) / len(y_true), tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
                roc_auc=float(roc_auc_score(y_true, prob)) if len(set(y_true)) > 1 else float("nan"),
                pr_auc=float(average_precision_score(y_true, prob)) if len(set(y_true)) > 1 else float("nan"))


def best_f1_threshold(y_true, prob) -> float:
    """Pick the threshold on VALIDATION data only (never on test)."""
    ts = np.linspace(0.05, 0.95, 91)
    return float(ts[int(np.argmax([report(y_true, prob, t)["f1"] for t in ts]))])
