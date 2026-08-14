# Stock Data Loader

ETL: Odoo stock on-hand + lots + valuation → PostgreSQL `raw.*`.

```bash
make up SERVICE=stock ENV=dev
python -m loaders.stock_data_loader.src.main
```

See [docs/loaders/stock.md](../../docs/loaders/stock.md).
