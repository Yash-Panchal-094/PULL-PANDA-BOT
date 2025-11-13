#include <iostream>
#include <vector>

class Solution {
public:
    int search(std::vector<int>& nums, int target) {
        int left = 0;
        int right = nums.size() - 1;

        while (left <= right) {
            int mid = left + (right - left) / 2;

            if (nums[mid] == target) {
                return mid;
            }

            if (nums[left] <= nums[mid]) {
                if (target > nums[left] && target < nums[mid]) {
                    right = mid - 1;
                } else {
                    left = mid + 1;
                }
            } else {
                if (target > nums[mid] && target <= nums[right]) {
                    left = mid + 1;
                } else {
                    right = mid - 1;
                }
            }
        }
        return -1;
    }
};

int main() {
    // Create your own set of demo test cases and test on your own and fix the errors
    
    // Example:
     Solution s;
     std::vector<int> my_nums = {4, 5, 6, 7, 0, 1, 2};
     int my_target = 4;
     std::cout << "Result: " << s.search(my_nums, my_target) << std::endl;

    return 0;
}
