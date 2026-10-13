"""Legacy entry point; use the shared Parquet cleaning and normalized loader."""

if __package__:
    from .data_pipeline import main
else:
    from data_pipeline import main


if __name__ == '__main__':
    main()
