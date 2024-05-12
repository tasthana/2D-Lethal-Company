"""
For use in the game loop, helper functions
"""


import numpy as np
import matplotlib.pyplot as plt


def increase_quota(current_quota, quotas_fulfilled):
    """
    Based off this: https://lethal-company.fandom.com/wiki/Profit_Quota
    :param current_quota: Int, Current quota amount
    :param quotas_fulfilled: Int, quotas fulfilled (This will be 1 after completing the first quota)
    :return: Int, next quota
    """
    randomizer_curve = generate_randomizer_curve(1000)
    random_choice = np.random.choice(randomizer_curve, 1)
    next_quota = current_quota + 100 * (1 + quotas_fulfilled ** 2 / 16) * (random_choice + 1)

    # Code to plot the curve
    """
    plt.figure(figsize=(8, 6))
    plt.hist(randomizer_curve, bins=30, density=True, color='skyblue', edgecolor='black', alpha=0.7)
    plt.title('Randomizer Curve')
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.show()
    """
    return int(next_quota[0])


def generate_randomizer_curve(size):
    """
    This is in effort to emulate the quota randomizer curve. There are other ways to do this,
    but this works well enough
    :param size:
    :return:
    """
    # Generate normally distributed random numbers
    mean = 0
    std_dev = 0.1  # Adjust standard deviation as needed
    rand_nums = np.random.normal(mean, std_dev, size)

    # Adjust range to [-0.5, 0.5]
    rand_nums = np.clip(rand_nums, -0.5, 0.5)

    # Apply bias towards zero
    bias_factor = 0.5  # Adjust as needed
    rand_nums *= np.exp(-bias_factor * np.abs(rand_nums))

    return rand_nums

