cmake_minimum_required(VERSION 3.8)
project(aspn_vn100)


if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)
find_package(eigen3_cmake_module)
find_package(Eigen3 REQUIRED)

find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

set(VN100_SOURCE_FILES
   src/vn100_processing.cpp          
)

add_executable(vn100_node ${VN100_SOURCE_FILES} )

ament_target_dependencies(vn100_node
  "rclcpp" "std_msgs" "Eigen3" "sensor_msgs"
)

install(TARGETS vn100_node
 DESTINATION lib/${PROJECT_NAME})


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
