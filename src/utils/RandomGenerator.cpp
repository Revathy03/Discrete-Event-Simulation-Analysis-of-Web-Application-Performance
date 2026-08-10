#include "RandomGenerator.h"

RandomGenerator::RandomGenerator(unsigned int seed) : rng(seed) {}

double RandomGenerator::exponential(double mean) {
    if (mean <= 0) return 0;
    std::exponential_distribution<double> dist(1.0 / mean);
    return dist(rng);
}

double RandomGenerator::uniform(double a, double b) {
    std::uniform_real_distribution<double> dist(a, b);
    return dist(rng);
}

double RandomGenerator::constant(double value) {
    return value;
}

double RandomGenerator::generate_think_time(double mean, DistributionType dist) {
    switch (dist) {
        case DistributionType::CONSTANT:
            return constant(mean);
        case DistributionType::UNIFORM:
            return uniform(0.0, 2.0 * mean);
        case DistributionType::EXPONENTIAL:
        default:
            return exponential(mean);
    }
}

double RandomGenerator::generate_service_time(double mean, DistributionType dist) {
    switch (dist) {
        case DistributionType::CONSTANT:
            return constant(mean);
        case DistributionType::UNIFORM:
            // Uniform between 0 and 2*mean (mean is the average)
            return uniform(0.0, 2.0 * mean);
        case DistributionType::EXPONENTIAL:
        default:
            return exponential(mean);
    }
}

double RandomGenerator::generate_timeout(double min_val, double var_val) {
    // "Have some sort of a minimum, and then a variable component"
    return min_val + exponential(var_val);
}
