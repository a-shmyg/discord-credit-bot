import datetime

def get_future_dates(number_of_days):
    print(f"Getting next {number_of_days} in the future...")
    future_dates = []
    current_date = datetime.datetime.now()

    for i in range(number_of_days):
        future_date = current_date + datetime.timedelta(days=i)
        future_dates.append(future_date.strftime("%A %d %B (%d/%m/%Y)"))

    return future_dates

print(get_future_dates(10))