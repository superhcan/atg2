import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, log_loss
import logging
import datetime
import json
from pathlib import Path

def train_baseline():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Ladda data
    logger.info("Laddar träningsdata...")
    df = pd.read_csv('data/processed/train_ready.csv')
    df['date'] = pd.to_datetime(df['date'])
    
    # Definiera Split
    split_date = '2026-01-05'
    train_df = df[df['date'] < split_date].copy()
    test_df = df[df['date'] >= split_date].copy()
    
    logger.info(f"Träningsdata: {len(train_df)} rader")
    logger.info(f"Testdata: {len(test_df)} rader")
    
    # Features att använda
    ignore_cols = ['race_id', 'date', 'start_time', 'finish_order', 'target_win', 'final_odds', 'odds_5m', 'odds_30m', 'horse_name']
    features = [c for c in df.columns if c not in ignore_cols]
    
    logger.info(f"Tränar med {len(features)} features")
    
    X_train = train_df[features]
    y_train = train_df['target_win']
    X_test = test_df[features]
    y_test = test_df['target_win']
    
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)
    
    params = {
        'max_depth': 6,
        'eta': 0.1,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': 42
    }
    
    logger.info("Startar träning...")
    model = xgb.train(
        params, 
        dtrain, 
        num_boost_round=500, 
        evals=[(dtrain, 'train'), (dtest, 'test')], 
        early_stopping_rounds=50,
        verbose_eval=50
    )
    
    # Utvärdera
    y_pred = model.predict(dtest)
    test_df['pred_win_prob'] = y_pred
    
    auc = roc_auc_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred)
    
    logger.info(f"Test AUC: {auc:.4f}")
    
    # --- ROI Analys ---
    test_df['eval_odds'] = test_df['odds_5m'].fillna(test_df['final_odds'])
    test_df['implied_prob'] = 1 / test_df['eval_odds']
    test_df['edge'] = test_df['pred_win_prob'] / test_df['implied_prob']
    play_df = test_df.dropna(subset=['eval_odds'])
    
    roi_results = {}
    for threshold in [1.0, 1.1, 1.2, 1.5]:
        bets = play_df[play_df['edge'] > threshold]
        n_bets = len(bets)
        cost = n_bets
        wins = bets[bets['target_win'] == 1]
        revenue = wins['eval_odds'].sum()
        roi = (revenue - cost) / cost if cost > 0 else 0
        roi_results[f"edge_{threshold}"] = {"n_bets": int(n_bets), "roi": float(roi)}
        logger.info(f"Edge > {threshold}: {n_bets} spel. ROI: {roi:.2%}")

    # --- Versionering & Sparning ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    version_name = f"{timestamp}_xgboost"
    version_dir = Path(f"models/versions/{version_name}")
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Spara i version-mapp
    model.save_model(str(version_dir / "model.json"))
    test_df.to_csv(version_dir / "predictions.csv", index=False)
    
    metadata = {
        "version": version_name,
        "timestamp": timestamp,
        "split_date": split_date,
        "features": features,
        "params": params,
        "metrics": {
            "auc": float(auc),
            "logloss": float(logloss)
        },
        "roi_summary": roi_results
    }
    with open(version_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # Spara även som "current" i rooten (legacy support + enkelhet)
    model.save_model('models/xgboost_latest.json') # Bytte namn från baseline till latest
    test_df.to_csv('data/processed/test_predictions.csv', index=False)
    
    logger.info(f"Modell sparad i version: {version_name}")

if __name__ == "__main__":
    train_baseline()
