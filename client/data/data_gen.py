from random import randint, gauss
from sys import argv


def generate_data(filename, size):
    headers = "id_,age,wealth,gender"
    out = [headers]
    out_helper = [headers]
    for i in range(size):
        
        age = abs(int(gauss(50, 15)))

        # invalid data
        if randint(0, 100) < 5:
            age = randint(2**16, 2**32)

        #age_mask = randint(1, 2**32)
        #age_helper = (age - age_mask) % 2**32
        wealth = randint(0, 250000)
        #wealth_mask = randint(1, 2**32)
        #wealth_helper = (wealth - wealth_mask) % 2**32
        gender = randint(0, 1)
        #gender_mask = randint(1, 2**32)
        #gender_helper = (gender - gender_mask) % 2**32

        out.append(f"{i},{age},{wealth},{gender}")
        #out_helper.append(f"{i},{age_helper},{wealth_helper},{gender_helper}")

    with open(filename + ".csv", "w") as f:
        f.write("\n".join(out))

    #with open(filename + "Helper.csv", "w") as f:
    #    f.write("\n".join(out_helper))



if __name__ == "__main__":
    if len(argv) == 2:
        generate_data(argv[1], 1000)
    elif len(argv) > 2:
        generate_data(argv[1], int(argv[2]))
    else:
        generate_data("data", 1000)