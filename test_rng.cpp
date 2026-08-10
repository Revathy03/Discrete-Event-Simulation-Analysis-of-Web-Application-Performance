#include "src/utils/RandomGenerator.h"
#include <iostream>

int main() {
    RandomGenerator rg1(42);
    RandomGenerator rg2(42);
    RandomGenerator rg3(42);
    
    std::cout << "CONSTANT: " << rg1.generate_think_time(7.152, DistributionType::CONSTANT) << std::endl;
    std::cout << "UNIFORM: " << rg2.generate_think_time(7.152, DistributionType::UNIFORM) << std::endl;
    std::cout << "EXPONENTIAL: " << rg3.generate_think_time(7.152, DistributionType::EXPONENTIAL) << std::endl;
    
    return 0;
}
